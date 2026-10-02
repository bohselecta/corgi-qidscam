"""Quantum-inspired destructive search with content-addressed memory.

The implementation is classical. "Interference" refers to signed/phase-aware
aggregation of evidence vectors, not simulation of qubits and not quantum
speedup. The research question is whether persistent content identity plus
conflict learning can reduce repeated work in graph-shaped AI reasoning.
"""

from __future__ import annotations

import copy
import math
import time
from dataclasses import asdict, dataclass, field
from statistics import fmean
from typing import Any, Literal

from .canonical import canonical_json, cid_for
from .merkle import MerkleStore
from .schema import Candidate, Evidence, Problem, Proposition, _number

Status = Literal["survives", "destroyed", "uncertain"]


@dataclass(frozen=True, slots=True)
class SolverConfig:
    name: str
    content_addressed_memory: bool = True
    destructive_pruning: bool = True
    learn_nogoods: bool = True
    fail_first: bool = True
    phase_aggregation: bool = True
    destroy_below: float = -0.20
    uncertain_band: float = 0.08
    dependency_weight: float = 0.65

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("config name required")
        for name in (
            "content_addressed_memory",
            "destructive_pruning",
            "learn_nogoods",
            "fail_first",
            "phase_aggregation",
        ):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be boolean")
        for name in ("destroy_below", "uncertain_band", "dependency_weight"):
            _number(getattr(self, name), name)
        if (
            not -1 <= self.destroy_below < 0
            or not 0 <= self.uncertain_band <= 1
            or not 0 <= self.dependency_weight <= 1
        ):
            raise ValueError("config thresholds/weights outside supported bounds")

    def canonical(self) -> dict[str, Any]:
        return asdict(self)


BASELINE_CONFIG = SolverConfig(
    name="independent-exhaustive",
    content_addressed_memory=False,
    destructive_pruning=False,
    learn_nogoods=False,
    fail_first=False,
)

DESTRUCTIVE_ONLY_CONFIG = SolverConfig(
    name="destructive-only",
    content_addressed_memory=False,
    destructive_pruning=True,
    learn_nogoods=False,
    fail_first=True,
)

MERKLE_ONLY_CONFIG = SolverConfig(
    name="merkle-memory-only",
    content_addressed_memory=True,
    destructive_pruning=False,
    learn_nogoods=False,
    fail_first=False,
)

QIDS_CAM_CONFIG = SolverConfig(name="qids-cam")
MAX_EXPANSIONS = 250_000


@dataclass(slots=True)
class Metrics:
    candidate_evaluations: int = 0
    proposition_expansions: int = 0
    evidence_reads: int = 0
    memo_hits: int = 0
    nogood_hits: int = 0
    learned_nogoods: int = 0
    destroyed_propositions: int = 0
    destroyed_candidates: int = 0
    early_prunes: int = 0
    avoided_requirements: int = 0
    unique_merkle_nodes: int = 0
    elapsed_ms: float = 0.0

    def deterministic(self) -> dict[str, int]:
        value = asdict(self)
        value.pop("elapsed_ms", None)
        return value  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class PropositionResult:
    key: str
    cid: str
    status: Status
    score: float
    local_score: float
    amplitude_real: float
    amplitude_imag: float
    coherence: float
    support: float
    opposition: float
    reason: str
    dependency_cids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CandidateResult:
    key: str
    label: str
    cid: str
    status: Status
    score: float
    reason: str
    evaluated_requirements: tuple[str, ...]
    skipped_requirements: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TraceEvent:
    step: int
    event: str
    subject: str
    cid: str
    detail: str
    status: Status | None = None
    score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CompiledProblem:
    problem_root: str
    evidence_cids: dict[str, str]
    proposition_cids: dict[str, str]
    candidate_cids: dict[str, str]


@dataclass(slots=True)
class SolveResult:
    config: SolverConfig
    problem_id: str
    problem_root: str
    proof_root: str
    winner: str | None
    candidate_results: tuple[CandidateResult, ...]
    proposition_results: dict[str, PropositionResult]
    metrics: Metrics
    trace: tuple[TraceEvent, ...]
    store: MerkleStore = field(repr=False)

    def to_dict(self, *, include_trace: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema": "qids-cam/solve-result/v1",
            "config": self.config.canonical(),
            "problem_id": self.problem_id,
            "problem_root": self.problem_root,
            "proof_root": self.proof_root,
            "winner": self.winner,
            "candidate_results": [item.to_dict() for item in self.candidate_results],
            "proposition_results": {
                key: self.proposition_results[key].to_dict()
                for key in sorted(self.proposition_results)
            },
            "metrics": asdict(self.metrics),
        }
        if include_trace:
            result["trace"] = [event.to_dict() for event in self.trace]
        return result


class QIDSCAMSolver:
    """Solve a candidate/evidence problem under a selectable ablation config."""

    def __init__(self, config: SolverConfig = QIDS_CAM_CONFIG) -> None:
        self.config = config
        self.store = MerkleStore()
        self.metrics = Metrics()
        self.trace: list[TraceEvent] = []
        self._memo: dict[tuple[str, str, str], PropositionResult] = {}
        self._nogoods: dict[tuple[str, str, str], PropositionResult] = {}
        self._compiled: CompiledProblem | None = None
        self._problem: Problem | None = None
        self._context_cid = cid_for({}, namespace="qids-cam-context-v1")
        self._result_by_key: dict[str, PropositionResult] = {}
        self._hazard_cache: dict[str, float] = {}

    def _emit(
        self,
        event: str,
        subject: str,
        cid: str,
        detail: str,
        *,
        status: Status | None = None,
        score: float | None = None,
    ) -> None:
        self.trace.append(
            TraceEvent(
                step=len(self.trace) + 1,
                event=event,
                subject=subject,
                cid=cid,
                detail=detail,
                status=status,
                score=None if score is None else round(score, 8),
            )
        )

    def compile(self, problem: Problem) -> CompiledProblem:
        evidence_cids: dict[str, str] = {}
        for key in sorted(problem.evidence):
            evidence = problem.evidence[key]
            payload = {
                "text": evidence.text,
                "stance": evidence.stance,
                "confidence": evidence.confidence,
                "source": evidence.source,
                "phase_degrees": evidence.phase_degrees,
                "tags": list(evidence.tags),
            }
            evidence_cids[key] = self.store.put("evidence", payload)

        proposition_cids: dict[str, str] = {}
        compiling: set[str] = set()

        def compile_proposition(key: str) -> str:
            if key in proposition_cids:
                return proposition_cids[key]
            if key in compiling:
                raise ValueError(f"cycle encountered while compiling {key!r}")
            compiling.add(key)
            proposition = problem.propositions[key]
            dependency_cids = [
                compile_proposition(item) for item in proposition.depends_on
            ]
            linked_evidence = [evidence_cids[item] for item in proposition.evidence]
            # Deliberately omit the local alias/key. Semantically identical nodes
            # receive one CID even when they entered the problem under two names.
            payload = {
                "statement": proposition.statement,
                "evidence": sorted(linked_evidence),
                "dependencies": sorted(dependency_cids),
                "metadata": proposition.metadata,
                "evaluation_schema": "qids-cam-evidence-v1",
            }
            cid = self.store.put(
                "proposition",
                payload,
                links=(*linked_evidence, *dependency_cids),
            )
            proposition_cids[key] = cid
            compiling.remove(key)
            return cid

        for key in sorted(problem.propositions):
            compile_proposition(key)

        candidate_cids: dict[str, str] = {}
        for candidate in problem.candidates:
            requirement_cids = [proposition_cids[item] for item in candidate.requires]
            candidate_cids[candidate.key] = self.store.put(
                "candidate",
                {
                    "label": candidate.label,
                    "prior": candidate.prior,
                    "requirements": sorted(requirement_cids),
                },
                links=requirement_cids,
            )

        problem_root = self.store.put(
            "problem",
            {
                "problem_id": problem.problem_id,
                "query": problem.query,
                "metadata": problem.metadata,
                "candidates": [candidate_cids[item.key] for item in problem.candidates],
            },
            links=candidate_cids.values(),
        )
        compiled = CompiledProblem(
            problem_root=problem_root,
            evidence_cids=evidence_cids,
            proposition_cids=proposition_cids,
            candidate_cids=candidate_cids,
        )
        self._compiled = compiled
        return compiled

    def solve(
        self,
        problem: Problem,
        *,
        constraints: dict[str, Any] | None = None,
    ) -> SolveResult:
        # A solve is an isolated cold computation. No unverified prior state can
        # enter its proof or learned no-goods, including on solver reuse.
        self.__init__(self.config)
        problem = Problem.from_dict(copy.deepcopy(problem.to_dict()))
        if constraints is not None and not isinstance(constraints, dict):
            raise ValueError("constraints must be an object")
        constraints = copy.deepcopy(constraints or {})
        canonical_json(constraints)
        started = time.perf_counter()
        self._problem = problem
        compiled = self.compile(problem)
        self._context_cid = cid_for(
            constraints, namespace="qids-cam-constraint-context-v1"
        )
        candidate_results: list[CandidateResult] = []

        for candidate in problem.candidates:
            candidate_results.append(self._evaluate_candidate(candidate))

        survivors = [item for item in candidate_results if item.status != "destroyed"]
        winner = (
            max(survivors, key=lambda item: (item.score, item.key)).key
            if survivors
            else None
        )

        result_nodes: list[str] = []
        for candidate_result in candidate_results:
            result_nodes.append(
                self.store.put(
                    "candidate-result",
                    {
                        "candidate": candidate_result.cid,
                        "status": candidate_result.status,
                        "score": round(candidate_result.score, 12),
                        "reason": candidate_result.reason,
                        "evaluated_requirements": list(
                            candidate_result.evaluated_requirements
                        ),
                        "skipped_requirements": list(
                            candidate_result.skipped_requirements
                        ),
                    },
                    links=(candidate_result.cid,),
                )
            )

        input_cid = self.store.put(
            "solve-input", {"problem": problem.to_dict(), "constraints": constraints}
        )
        context_node = self.store.put(
            "constraint-context",
            {"context_cid": self._context_cid, "constraints": constraints},
        )
        trace_cid = self.store.put(
            "execution-trace", {"events": [event.to_dict() for event in self.trace]}
        )
        states_cid = self.store.put(
            "resolved-states",
            {
                "propositions": {
                    key: self._result_by_key[key].to_dict()
                    for key in sorted(self._result_by_key)
                }
            },
        )
        self.metrics.unique_merkle_nodes = len(self.store) + 1
        proof_root = self.store.put(
            "solve-proof",
            {
                "proof_schema": "qids-cam/solve-proof/v2",
                "solver": self.config.canonical(),
                "problem_root": compiled.problem_root,
                "input": input_cid,
                "trace": trace_cid,
                "states": states_cid,
                "context_node": context_node,
                "context": self._context_cid,
                "winner": winner,
                "candidates": [x.to_dict() for x in candidate_results],
                "metrics": self.metrics.deterministic(),
                "algorithm_version": "0.2.0",
            },
            links=(
                compiled.problem_root,
                input_cid,
                context_node,
                trace_cid,
                states_cid,
                *result_nodes,
            ),
        )
        self.metrics.elapsed_ms = (time.perf_counter() - started) * 1000.0

        if not self.store.verify(proof_root, recursive=True):
            raise RuntimeError("internal proof DAG verification failed")

        return SolveResult(
            config=self.config,
            problem_id=problem.problem_id,
            problem_root=compiled.problem_root,
            proof_root=proof_root,
            winner=winner,
            candidate_results=tuple(candidate_results),
            proposition_results=dict(self._result_by_key),
            metrics=self.metrics,
            trace=tuple(self.trace),
            store=self.store,
        )

    def _phase(self, evidence: Evidence) -> float:
        if not self.config.phase_aggregation:
            return 0.0 if evidence.stance > 0 else math.pi
        if evidence.phase_degrees is not None:
            return math.radians(evidence.phase_degrees)
        return 0.0 if evidence.stance > 0 else math.pi

    def _local_evidence(
        self, proposition: Proposition
    ) -> tuple[float, float, float, float, float, float]:
        assert self._problem is not None
        real = 0.0
        imag = 0.0
        support = 0.0
        opposition = 0.0
        total = 0.0
        for evidence_key in sorted(
            proposition.evidence, key=lambda k: self._compiled.evidence_cids[k]
        ):
            evidence = self._problem.evidence[evidence_key]
            self.metrics.evidence_reads += 1
            weight = evidence.confidence
            phase = self._phase(evidence)
            real += weight * math.cos(phase)
            imag += weight * math.sin(phase)
            total += weight
            if evidence.stance > 0:
                support += weight
            else:
                opposition += weight
        if total == 0.0:
            return 0.0, 0.0, 0.0, 0.0, support, opposition
        local_score = max(-1.0, min(1.0, real / total))
        coherence = min(1.0, math.hypot(real, imag) / total)
        return real, imag, local_score, coherence, support, opposition

    def _status_for_score(self, score: float) -> Status:
        if score <= self.config.destroy_below:
            return "destroyed"
        if abs(score) <= self.config.uncertain_band:
            return "uncertain"
        return "survives"

    def _hazard(self, key: str) -> float:
        cached = self._hazard_cache.get(key)
        if cached is not None:
            return cached
        assert self._problem is not None
        proposition = self._problem.propositions[key]
        support = sum(
            self._problem.evidence[item].confidence
            for item in proposition.evidence
            if self._problem.evidence[item].stance > 0
        )
        opposition = sum(
            self._problem.evidence[item].confidence
            for item in proposition.evidence
            if self._problem.evidence[item].stance < 0
        )
        local = opposition - support
        child_hazard = max(
            (self._hazard(item) for item in proposition.depends_on), default=0.0
        )
        hazard = local + 0.8 * child_hazard
        self._hazard_cache[key] = hazard
        return hazard

    def _evaluate_proposition(self, key: str) -> PropositionResult:
        assert self._problem is not None and self._compiled is not None
        proposition = self._problem.propositions[key]
        cid = self._compiled.proposition_cids[key]
        cache_key = (
            cid,
            self._context_cid,
            cid_for(self.config.canonical(), namespace="qids-cam-evaluation-config-v2"),
        )

        if self.config.learn_nogoods and cache_key in self._nogoods:
            self.metrics.nogood_hits += 1
            result = self._nogoods[cache_key]
            aliased = PropositionResult(
                key=key,
                cid=result.cid,
                status=result.status,
                score=result.score,
                local_score=result.local_score,
                amplitude_real=result.amplitude_real,
                amplitude_imag=result.amplitude_imag,
                coherence=result.coherence,
                support=result.support,
                opposition=result.opposition,
                reason=f"nogood reuse: {result.reason}",
                dependency_cids=result.dependency_cids,
            )
            self._result_by_key[key] = aliased
            self._emit(
                "nogood-hit",
                key,
                cid,
                aliased.reason,
                status=aliased.status,
                score=aliased.score,
            )
            return aliased

        if self.config.content_addressed_memory and cache_key in self._memo:
            self.metrics.memo_hits += 1
            result = self._memo[cache_key]
            aliased = PropositionResult(
                key=key,
                cid=result.cid,
                status=result.status,
                score=result.score,
                local_score=result.local_score,
                amplitude_real=result.amplitude_real,
                amplitude_imag=result.amplitude_imag,
                coherence=result.coherence,
                support=result.support,
                opposition=result.opposition,
                reason=f"CID memo reuse: {result.reason}",
                dependency_cids=result.dependency_cids,
            )
            self._result_by_key[key] = aliased
            self._emit(
                "memo-hit",
                key,
                cid,
                aliased.reason,
                status=aliased.status,
                score=aliased.score,
            )
            return aliased

        if self.metrics.proposition_expansions >= MAX_EXPANSIONS:
            raise ValueError("solve exceeds 250000 proposition expansion budget")
        self.metrics.proposition_expansions += 1
        self._emit("expand", key, cid, proposition.statement)
        real, imag, local_score, coherence, support, opposition = (
            round(x, 12) for x in self._local_evidence(proposition)
        )
        local_status = self._status_for_score(local_score)

        # Destructive evaluation checks a locally fatal contradiction before
        # spending work on descendants.
        if self.config.destructive_pruning and local_status == "destroyed":
            result = PropositionResult(
                key=key,
                cid=cid,
                status="destroyed",
                score=local_score,
                local_score=local_score,
                amplitude_real=real,
                amplitude_imag=imag,
                coherence=coherence,
                support=support,
                opposition=opposition,
                reason="destructive cancellation: local opposing amplitude dominates",
                dependency_cids=tuple(
                    self._compiled.proposition_cids[item]
                    for item in proposition.depends_on
                ),
            )
            self.metrics.destroyed_propositions += 1
            self._remember(cache_key, result)
            self._result_by_key[key] = result
            self._emit(
                "destroy",
                key,
                cid,
                result.reason,
                status=result.status,
                score=result.score,
            )
            return result

        dependency_keys = sorted(
            proposition.depends_on, key=lambda k: self._compiled.proposition_cids[k]
        )
        if self.config.fail_first:
            dependency_keys.sort(key=self._hazard, reverse=True)
        dependency_results = [
            self._evaluate_proposition(item) for item in dependency_keys
        ]
        destroyed_dependencies = [
            item for item in dependency_results if item.status == "destroyed"
        ]

        if local_status == "destroyed":
            # Exhaustive mode spends work on all children but cannot rescue a
            # fatal local contradiction. This is semantics, not an optimization.
            status = "destroyed"
            score = local_score
            reason = "destructive cancellation: local opposing amplitude dominates"
        elif destroyed_dependencies:
            status: Status = "destroyed"
            score = min(item.score for item in destroyed_dependencies)
            reason = f"dependency destroyed: {destroyed_dependencies[0].cid}"
        else:
            dependency_scores = [item.score for item in dependency_results]
            if proposition.evidence and dependency_scores:
                dep_mean = fmean(dependency_scores)
                score = (
                    1.0 - self.config.dependency_weight
                ) * local_score + self.config.dependency_weight * dep_mean
            elif dependency_scores:
                score = fmean(dependency_scores)
            else:
                score = local_score
            score = max(-1.0, min(1.0, score))
            status = self._status_for_score(score)
            if status == "destroyed":
                reason = (
                    "combined evidence and dependencies fall below survival threshold"
                )
            elif status == "uncertain":
                reason = "constructive and destructive contributions nearly cancel"
            else:
                reason = "residual support survives destructive evaluation"

        result = PropositionResult(
            key=key,
            cid=cid,
            status=status,
            score=round(score, 12),
            local_score=local_score,
            amplitude_real=real,
            amplitude_imag=imag,
            coherence=coherence,
            support=support,
            opposition=opposition,
            reason=reason,
            dependency_cids=tuple(item.cid for item in dependency_results),
        )
        if status == "destroyed":
            self.metrics.destroyed_propositions += 1
        self._remember(cache_key, result)
        self._result_by_key[key] = result
        self._emit(
            "destroy" if status == "destroyed" else "resolve",
            key,
            cid,
            reason,
            status=status,
            score=score,
        )
        return result

    def _remember(
        self,
        cache_key: tuple[str, str, str],
        result: PropositionResult,
    ) -> None:
        if self.config.content_addressed_memory:
            self._memo[cache_key] = result
        if self.config.learn_nogoods and result.status == "destroyed":
            if cache_key not in self._nogoods:
                self.metrics.learned_nogoods += 1
            self._nogoods[cache_key] = result

    def _evaluate_candidate(self, candidate: Candidate) -> CandidateResult:
        assert self._compiled is not None
        self.metrics.candidate_evaluations += 1
        cid = self._compiled.candidate_cids[candidate.key]
        requirements = (
            sorted(candidate.requires, key=lambda k: self._compiled.proposition_cids[k])
            if self.config.fail_first
            else list(candidate.requires)
        )
        if self.config.fail_first:
            requirements.sort(key=self._hazard, reverse=True)

        evaluated: list[str] = []
        skipped: list[str] = []
        requirement_results: list[PropositionResult] = []
        destroyed: PropositionResult | None = None

        self._emit("candidate", candidate.key, cid, candidate.label)
        for index, requirement in enumerate(requirements):
            result = self._evaluate_proposition(requirement)
            evaluated.append(requirement)
            requirement_results.append(result)
            if self.config.destructive_pruning and result.status == "destroyed":
                destroyed = result
                skipped = requirements[index + 1 :]
                self.metrics.early_prunes += 1
                self.metrics.avoided_requirements += len(skipped)
                break

        # Exhaustive configurations evaluate every requirement before deciding.
        if destroyed is None:
            destroyed = next(
                (item for item in requirement_results if item.status == "destroyed"),
                None,
            )

        if destroyed is not None:
            status: Status = "destroyed"
            score = -1.0
            reason = f"requirement destroyed: {destroyed.key} ({destroyed.cid})"
        else:
            raw_scores = [item.score for item in requirement_results]
            score = round(
                candidate.prior + (fmean(sorted(raw_scores)) if raw_scores else 0.0), 12
            )
            score = max(-1.0, min(1.0, score))
            status = self._status_for_score(score)
            reason = (
                "all required propositions survived"
                if status == "survives"
                else "candidate remains unresolved"
            )

        if status == "destroyed":
            self.metrics.destroyed_candidates += 1
        self._emit(
            "candidate-destroyed" if status == "destroyed" else "candidate-resolved",
            candidate.key,
            cid,
            reason,
            status=status,
            score=score,
        )
        return CandidateResult(
            key=candidate.key,
            label=candidate.label,
            cid=cid,
            status=status,
            score=score,
            reason=reason,
            evaluated_requirements=tuple(evaluated),
            skipped_requirements=tuple(skipped),
        )


def run_all_ablations(problem: Problem) -> dict[str, SolveResult]:
    """Run the four reference configurations used by the benchmark."""

    configs = (
        BASELINE_CONFIG,
        DESTRUCTIVE_ONLY_CONFIG,
        MERKLE_ONLY_CONFIG,
        QIDS_CAM_CONFIG,
    )
    return {config.name: QIDSCAMSolver(config).solve(problem) for config in configs}
