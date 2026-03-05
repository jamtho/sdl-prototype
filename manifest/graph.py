"""Manifest graph loader — reads Turtle files and extracts structured metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.term import Node

from manifest.model import (
    AggregatedColumnInfo,
    AggregationInfo,
    ColumnInfo,
    DatasetInfo,
    DerivationInfo,
    OrderingKeyInfo,
    SemanticTypeInfo,
)

# Namespace declarations matching the Turtle files
MNF = Namespace("http://example.org/manifest#")
AIS = Namespace("http://example.org/ais#")
PM = Namespace("http://example.org/polymarket#")
RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
XSD = Namespace("http://www.w3.org/2001/XMLSchema#")


def _str(node: Node | None) -> str:
    """Convert an rdflib node to a compact prefixed string."""
    if node is None:
        return ""
    s = str(node)
    for prefix, ns in [("mnf:", str(MNF)), ("ais:", str(AIS)),
                        ("pm:", str(PM)),
                        ("rdfs:", str(RDFS)), ("xsd:", str(XSD))]:
        if s.startswith(ns):
            return prefix + s[len(ns):]
    return s


def _lit_float(node: Node | None) -> float | None:
    """Extract a float from a Literal node, or None."""
    if node is None:
        return None
    if isinstance(node, Literal):
        try:
            return float(node)
        except (ValueError, TypeError):
            return None
    return None


def _lit_str(node: Node | None) -> str:
    """Extract a string from a Literal or URI node."""
    if node is None:
        return ""
    return str(node)


def _label_or_str(g: Graph, node: Node | None) -> str:
    """For named individuals, return rdfs:label; for literals, return the value."""
    if node is None:
        return ""
    if isinstance(node, Literal):
        return str(node)
    label = g.value(node, RDFS.label)
    if label is not None:
        return str(label)
    return _str(node)


def _lit_bool(node: Node | None) -> bool:
    """Extract a boolean, defaulting to True for nullable."""
    if node is None:
        return True
    if isinstance(node, Literal):
        return str(node).lower() in ("true", "1")
    return True


class ManifestGraph:
    """
    Loads Manifest vocabulary and domain description files, provides
    structured query methods for extracting dataset metadata,
    constraints, derivations, and aggregation relationships.
    """

    def __init__(self) -> None:
        self.g = Graph()
        self.g.bind("mnf", MNF)
        self.g.bind("ais", AIS)
        self.g.bind("pm", PM)
        self.g.bind("rdfs", RDFS)
        self.g.bind("xsd", XSD)

    def load(self, path: str | Path) -> None:
        """Load a Turtle file into the graph."""
        self.g.parse(str(path), format="turtle")

    def load_directory(self, directory: str | Path) -> None:
        """Load all .ttl files from a directory."""
        d = Path(directory)
        for f in sorted(d.glob("*.ttl")):
            self.load(f)

    # -----------------------------------------------------------------
    # Dataset queries
    # -----------------------------------------------------------------

    def list_datasets(self) -> list[str]:
        """Return URIs of all declared datasets."""
        return [
            _str(s) for s in self.g.subjects(RDF.type, MNF.Dataset)
        ]

    def get_dataset(self, dataset_uri: str) -> DatasetInfo:
        """Resolve full metadata for a dataset."""
        subj = self._resolve_uri(dataset_uri)

        label = _lit_str(self.g.value(subj, RDFS.label)) or dataset_uri
        columns = list(self._get_columns(subj))
        ordering = list(self._get_ordering(subj))
        file_format, path_template, granularity, redundant_key = self._get_layout(subj)

        return DatasetInfo(
            uri=dataset_uri,
            label=label,
            columns=columns,
            file_format=file_format,
            ordering_keys=ordering,
            partition_path_template=path_template,
            partition_granularity=granularity,
            redundant_partition_key=redundant_key,
        )

    def _get_columns(self, dataset: URIRef) -> Iterator[ColumnInfo]:
        """Yield ColumnInfo for each column of a dataset."""
        for col_node in self.g.objects(dataset, MNF.hasColumn):
            name = _lit_str(self.g.value(col_node, MNF.columnName))
            phys = _str(self.g.value(col_node, MNF.physicalType))
            sem = _str(self.g.value(col_node, MNF.semanticType)) or None
            nullable = _lit_bool(self.g.value(col_node, MNF.nullable))
            yield ColumnInfo(
                uri=_str(col_node),
                name=name,
                physical_type=phys,
                semantic_type=sem,
                nullable=nullable,
            )

    def _get_ordering(self, dataset: URIRef) -> Iterator[OrderingKeyInfo]:
        """Yield ordering keys for a dataset's physical layout."""
        layout = self.g.value(dataset, MNF.hasPhysicalLayout)
        if layout is None:
            return
        ordering = self.g.value(layout, MNF.hasRowOrdering)
        if ordering is None:
            return
        for key_node in self.g.objects(ordering, MNF.hasOrderingKey):
            col_ref = self.g.value(key_node, MNF.keyColumn)
            col_name = _lit_str(self.g.value(col_ref, MNF.columnName)) if col_ref else ""
            direction = _label_or_str(self.g, self.g.value(key_node, MNF.keyDirection))
            precedence_lit = self.g.value(key_node, MNF.keyPrecedence)
            precedence = int(precedence_lit) if precedence_lit else 99
            semantic = _str(self.g.value(key_node, MNF.orderingSemantic))
            yield OrderingKeyInfo(
                column_name=col_name,
                direction=direction,
                precedence=precedence,
                semantic=semantic,
            )

    def _get_layout(self, dataset: URIRef) -> tuple[str, str | None, str | None, str | None]:
        """Extract physical layout info: format, path template, granularity, redundant key."""
        layout = self.g.value(dataset, MNF.hasPhysicalLayout)
        file_format = _label_or_str(self.g, self.g.value(layout, MNF.fileFormat)) if layout else "Parquet"

        partition = self.g.value(dataset, MNF.partitionedBy)
        path_template = _lit_str(self.g.value(partition, MNF.pathTemplate)) if partition else None
        granularity = _label_or_str(self.g, self.g.value(partition, MNF.partitionGranularity)) if partition else None

        # Handle CompositePartitionScheme
        if not granularity and partition and (partition, RDF.type, MNF.CompositePartitionScheme) in self.g:
            levels: list[tuple[int, str, str]] = []
            for level in self.g.objects(partition, MNF.hasPartitionLevel):
                prec_lit = self.g.value(level, MNF.levelPrecedence)
                prec = int(prec_lit) if prec_lit else 99
                col = _lit_str(self.g.value(level, MNF.levelColumn))
                gran = _label_or_str(self.g, self.g.value(level, MNF.levelGranularity))
                levels.append((prec, gran.lower() if gran else col, col))
            if levels:
                levels.sort()
                gran_parts = " + ".join(g for _, g, _ in levels)
                col_parts = ", ".join(c for _, _, c in levels)
                granularity = f"{gran_parts} ({col_parts})"

        redundant_key: str | None = None
        if partition:
            rk_node = self.g.value(partition, MNF.redundantPartitionKey)
            if rk_node:
                redundant_key = _lit_str(self.g.value(rk_node, MNF.columnName))

        return file_format, path_template, granularity, redundant_key

    # -----------------------------------------------------------------
    # Semantic type queries
    # -----------------------------------------------------------------

    def get_semantic_type(self, type_uri: str) -> SemanticTypeInfo | None:
        """Resolve metadata for a semantic type."""
        subj = self._resolve_uri(type_uri)
        if (subj, RDF.type, MNF.SemanticType) not in self.g:
            # Check if it's declared as a semantic type at all
            # (it might just be referenced without explicit rdf:type)
            if self.g.value(subj, MNF.requiredPhysicalType) is None:
                return None

        label = _lit_str(self.g.value(subj, RDFS.label)) or type_uri
        req_phys = _str(self.g.value(subj, MNF.requiredPhysicalType)) or None

        acceptable: list[str] = [
            _str(o) for o in self.g.objects(subj, MNF.acceptablePhysicalType)
        ]

        # Value range
        vr = self.g.value(subj, MNF.valueRange)
        min_inc = _lit_float(self.g.value(vr, MNF.minInclusive)) if vr else None
        max_inc = _lit_float(self.g.value(vr, MNF.maxInclusive)) if vr else None
        min_exc = _lit_float(self.g.value(vr, MNF.minExclusive)) if vr else None
        max_exc = _lit_float(self.g.value(vr, MNF.maxExclusive)) if vr else None

        unit = _lit_str(self.g.value(subj, MNF.unit)) or None

        return SemanticTypeInfo(
            uri=type_uri,
            label=label,
            required_physical_type=req_phys,
            acceptable_physical_types=acceptable,
            min_inclusive=min_inc,
            max_inclusive=max_inc,
            min_exclusive=min_exc,
            max_exclusive=max_exc,
            unit=unit,
        )

    # -----------------------------------------------------------------
    # Derivation queries
    # -----------------------------------------------------------------

    def get_derivations(self, dataset_uri: str) -> list[DerivationInfo]:
        """Find all derivations whose derived column belongs to this dataset."""
        dataset = self._resolve_uri(dataset_uri)
        dataset_columns = set(self.g.objects(dataset, MNF.hasColumn))

        derivations: list[DerivationInfo] = []
        for subj in self.g.subjects(RDF.type, MNF.Derivation):
            derived_col = self.g.value(subj, MNF.derivedColumn)
            if derived_col not in dataset_columns:
                continue

            derived_name = _lit_str(self.g.value(derived_col, MNF.columnName))
            source_cols = [
                _lit_str(self.g.value(sc, MNF.columnName))
                for sc in self.g.objects(subj, MNF.sourceColumn)
            ]
            func_uri = _str(self.g.value(subj, MNF.derivationFunction))
            props = [_str(p) for p in self.g.objects(subj, MNF.hasDerivationProperty)]

            derivations.append(DerivationInfo(
                uri=_str(subj),
                derived_column=derived_name,
                source_columns=source_cols,
                function_uri=func_uri,
                properties=props,
            ))

        return derivations

    # -----------------------------------------------------------------
    # Aggregation queries
    # -----------------------------------------------------------------

    def get_aggregations(self, target_dataset_uri: str) -> list[AggregationInfo]:
        """Find aggregation relationships targeting this dataset."""
        target = self._resolve_uri(target_dataset_uri)
        results: list[AggregationInfo] = []

        for subj in self.g.subjects(RDF.type, MNF.AggregationRelationship):
            if self.g.value(subj, MNF.targetDataset) != target:
                continue

            source_ds = _str(self.g.value(subj, MNF.sourceDataset))
            group_col_node = self.g.value(subj, MNF.groupByColumn)
            group_col = _lit_str(self.g.value(group_col_node, MNF.columnName)) if group_col_node else ""

            agg_cols: list[AggregatedColumnInfo] = []
            for ac_node in self.g.objects(subj, MNF.hasAggregatedColumn):
                tc_node = self.g.value(ac_node, MNF.targetColumn)
                tc_name = _lit_str(self.g.value(tc_node, MNF.columnName)) if tc_node else ""

                src_names = [
                    _lit_str(self.g.value(sc, MNF.columnName))
                    for sc in self.g.objects(ac_node, MNF.aggregationSourceColumn)
                ]

                func = _str(self.g.value(ac_node, MNF.aggregationFunction))

                order_node = self.g.value(ac_node, MNF.withinGroupOrdering)
                order_col = _lit_str(self.g.value(order_node, MNF.columnName)) if order_node else None

                agg_cols.append(AggregatedColumnInfo(
                    target_column=tc_name,
                    source_columns=src_names,
                    function_uri=func,
                    within_group_ordering=order_col,
                ))

            results.append(AggregationInfo(
                uri=_str(subj),
                source_dataset=source_ds,
                target_dataset=target_dataset_uri,
                group_by_column=group_col,
                aggregated_columns=agg_cols,
            ))

        return results

    # -----------------------------------------------------------------
    # Known deficiency queries
    # -----------------------------------------------------------------

    def get_known_deficiencies(self, dataset_uri: str) -> list[dict[str, str]]:
        """Return known deficiencies for a dataset."""
        dataset = self._resolve_uri(dataset_uri)
        deficiencies: list[dict[str, str]] = []
        for d_node in self.g.objects(dataset, MNF.hasKnownDeficiency):
            deficiencies.append({
                "description": _lit_str(self.g.value(d_node, MNF.deficiencyDescription)),
                "impact": _lit_str(self.g.value(d_node, MNF.impact)),
                "severity": _label_or_str(self.g, self.g.value(d_node, MNF.severity)),
            })
        return deficiencies

    # -----------------------------------------------------------------
    # Companion dataset queries
    # -----------------------------------------------------------------

    def get_companions(self, dataset_uri: str) -> list[str]:
        """Return URIs of companion datasets."""
        subj = self._resolve_uri(dataset_uri)
        companions: list[str] = []
        for obj in self.g.objects(subj, MNF.companionOf):
            companions.append(_str(obj))
        for s in self.g.subjects(MNF.companionOf, subj):
            companions.append(_str(s))
        return companions

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------

    def _resolve_uri(self, compact_uri: str) -> URIRef:
        """Resolve a prefixed URI like 'ais:DailyBroadcasts' to a full URIRef."""
        if compact_uri.startswith("http://") or compact_uri.startswith("https://"):
            return URIRef(compact_uri)
        prefix, _, local = compact_uri.partition(":")
        ns_map: dict[str, Namespace] = {
            "mnf": MNF,
            "ais": AIS,
            "pm": PM,
            "rdfs": RDFS,
            "xsd": XSD,
        }
        ns = ns_map.get(prefix)
        if ns:
            return ns[local]
        # Fallback: try bound namespaces in the graph
        for p, n in self.g.namespaces():
            if p == prefix:
                return URIRef(str(n) + local)
        return URIRef(compact_uri)

    def sparql(self, query: str) -> list[dict[str, str]]:
        """Run a raw SPARQL query and return results as list of dicts."""
        results = self.g.query(query)
        return [
            {str(var): _str(row[var]) for var in results.vars}
            for row in results
        ]
