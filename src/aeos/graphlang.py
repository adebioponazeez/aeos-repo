"""v39.6 The Graph Language: workflows as declarative, diffable DOT.

Fabro's sharpest ergonomics, compiled into AEOS law: the process is a
version-controlled graph (Graphviz DOT subset), the model routing is a
stylesheet (INI sections matched by fnmatch), and clusters are NESTED
HARNESSES — a `subgraph cluster_*` compiles to one parent task whose
subplan is the cluster's nodes (the v39.5 recursion, now declarative).

What the language is (and is not), honestly (ADR-052):
- IS: a DOT SUBSET — digraph, node stmts with [attrs], `->` chains,
  subgraph clusters, // and # comments, quoted strings. Not full DOT
  (no ports, no records, no HTML labels) — a named error says so.
- IS NOT: a bypass of the kernel. The compiler emits the SAME TaskSpec
  objects the orchestrator already runs; the same governor classifies
  every task; the same hooks intercept every point; the same gates
  grade every envelope. A declarative graph gets zero new trust.
- SAFETY LAW: a stylesheet may route (pick the adapter, tighten
  attempts, set a profile) but may NEVER change an action class —
  `class` on a stylesheet is a NAMED compile error. Routing that
  could declassify is not routing, it is sabotage.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path

from .contracts import ActionClass, TaskSpec
from .orchestrator import MAX_SUBPLAN_DEPTH

# ------------------------------------------------------------------ errors


class GraphError(Exception):
    """A named compile error in plain language (ADR-013). Never a
    SyntaxError traceback: the message is the remedy."""

    def __init__(self, msg: str, line: int = 0):
        super().__init__(f"line {line}: {msg}" if line else msg)
        self.line = line


# ------------------------------------------------------------------ lexer

_TOKEN = re.compile(r'''
    (?P<ws>\s+)
  | (?P<comment>//[^\n]*|\#[^\n]*)
  | (?P<qstr>"(?:[^"\\]|\\.)*")
  | (?P<arrow>->)
  | (?P<punct>[{}\[\];=,])
  | (?P<id>[A-Za-z_][A-Za-z0-9_.-]*)
''', re.VERBOSE)


@dataclass
class Tok:
    kind: str          # qstr | arrow | punct | id | EOF
    text: str
    line: int


def _lex(src: str) -> list[Tok]:
    out, pos, line = [], 0, 1
    while pos < len(src):
        m = _TOKEN.match(src, pos)
        if not m:
            raise GraphError(
                f"unexpected character {src[pos]!r} — the language is a "
                "DOT subset (ids, quoted strings, ->, {{}}, [], ;, =)",
                line)
        pos = m.end()
        line += src.count("\n", m.start(), m.end())
        if m.lastgroup in ("ws", "comment"):
            continue
        out.append(Tok(m.lastgroup, m.group(), line))
    out.append(Tok("EOF", "", line))
    return out


# ------------------------------------------------------------------ parser


class _Parser:
    def __init__(self, toks: list[Tok]):
        self.toks = toks
        self.i = 0

    def peek(self) -> Tok:
        return self.toks[self.i]

    def next(self) -> Tok:
        t = self.toks[self.i]
        self.i += 1
        return t

    def eat(self, kind: str, text: str | None = None) -> Tok:
        t = self.next()
        if t.kind != kind or (text is not None and t.text != text):
            want = text or kind
            raise GraphError(
                f"expected {want!r}, found {t.text or 'end of file'!r}",
                t.line)
        return t

    def unquote(self, t: Tok) -> str:
        if t.kind != "qstr":
            return t.text
        return re.sub(r'\\(.)', r'\1', t.text[1:-1])

    # ---- statements

    def parse(self) -> "_Graph":
        self.eat("id", "digraph")
        name = ""
        if self.peek().kind == "id":
            name = self.next().text
        g = _Graph(name)
        self._body(g, top=True)
        return g

    def _body(self, g: "_Graph", top: bool = False) -> None:
        self.eat("punct", "{")
        while not (self.peek().kind == "punct" and self.peek().text == "}"):
            if self.peek().kind == "EOF":
                raise GraphError("unterminated block — a '{' is missing "
                                 "its '}'", self.peek().line)
            self._stmt(g, top)
        self.eat("punct", "}")

    def _stmt(self, g: "_Graph", top: bool) -> None:
        t = self.peek()
        if t.kind == "id" and t.text == "subgraph":
            self.next()
            sname = ""
            if self.peek().kind == "id":
                sname = self.next().text
            sub = _Graph(sname)
            self._body(sub, top=False)
            g.children.append(sub)
            return
        if t.kind != "id":
            raise GraphError(
                f"expected a node name or 'subgraph', found "
                f"{t.text or 'end of file'!r}", t.line)
        first = self.next().text
        attrs = {}
        if self.peek().kind == "punct" and self.peek().text == "[":
            attrs = self._attrs()
        if not (self.peek().kind == "arrow"):
            g.node(first, attrs, t.line)
            self._semi()
            return
        # edge chain: a -> b -> c [attrs] — stored RAW; resolution
        # (local node / cluster parent / intra-cluster) is compile-time,
        # because a cross-level edge must NOT create phantom nodes.
        chain = [first]
        while self.peek().kind == "arrow":
            self.next()
            nt = self.eat("id")
            chain.append(nt.text)
        eattrs = {}
        if self.peek().kind == "punct" and self.peek().text == "[":
            eattrs = self._attrs()
        g.raw_chains.append((chain, eattrs, t.line))
        self._semi()

    def _attrs(self) -> dict:
        self.eat("punct", "[")
        attrs = {}
        while not (self.peek().kind == "punct" and self.peek().text == "]"):
            k = self.eat("id")
            self.eat("punct", "=")
            v = self.next()
            if v.kind == "qstr":
                attrs[k.text] = self.unquote(v)
            elif v.kind == "id":
                attrs[k.text] = v.text
            else:
                raise GraphError(
                    f"attribute {k.text!r} needs a value (quoted or id)",
                    v.line)
            if self.peek().kind == "punct" and self.peek().text == ",":
                self.next()
        self.eat("punct", "]")
        return attrs

    def _semi(self) -> None:
        if self.peek().kind == "punct" and self.peek().text == ";":
            self.next()


@dataclass
class _Node:
    name: str
    attrs: dict
    line: int


class _Graph:
    """Intermediate form: nodes, edges, child subgraphs."""

    def __init__(self, name: str):
        self.name = name
        self.nodes: dict[str, _Node] = {}
        self.order: list[str] = []
        self.raw_chains: list[tuple[list, dict, int]] = []
        self.children: list["_Graph"] = []

    def node(self, name: str, attrs: dict, line: int) -> None:
        if name not in self.nodes:
            self.order.append(name)
        self.nodes.setdefault(name, _Node(name, attrs, line))
        if attrs:
            self.nodes[name].attrs.update(attrs)




# ------------------------------------------------------------------ compile


def _mk_task(node: _Node) -> TaskSpec:
    agent = node.attrs.get("agent")
    if not agent:
        raise GraphError(
            f"node '{node.name}' has no agent — every node must name its "
            "agent (agent=\"...\") or be covered by a [pattern] section "
            "with agent=... in the stylesheet", node.line)
    cls = node.attrs.get("class", "READ")
    try:
        action_class = ActionClass(cls)
    except ValueError:
        raise GraphError(
            f"node '{node.name}' has unknown class {cls!r} — the classes "
            f"are: {', '.join(c.value for c in ActionClass)}", node.line)
    try:
        attempts = int(node.attrs.get("max_attempts", 2))
    except ValueError:
        raise GraphError(
            f"node '{node.name}' has a non-integer max_attempts", node.line)
    return TaskSpec(name=node.name,
                    description=node.attrs.get("label", node.name),
                    agent=agent, action_class=action_class,
                    max_attempts=attempts,
                    model=node.attrs.get("model"))


def compile_graph(src: str, style: str | None = None) -> list[TaskSpec]:
    """DOT source (+ optional stylesheet) -> the TaskSpec graph the
    orchestrator runs. Clusters become subplans; every error is named."""
    g = _Parser(_lex(src)).parse()
    style_map = parse_style(style) if style else {}

    def build(gr: _Graph, depth: int) -> list[TaskSpec]:
        if depth > MAX_SUBPLAN_DEPTH:
            raise GraphError(
                f"cluster '{gr.name}' nests deeper than {MAX_SUBPLAN_DEPTH} "
                "— recursion is a tool, not a trap (ADR-051)")
        tasks = {n: _mk_task(gr.nodes[n]) for n in gr.order}
        # child clusters -> one parent task with the cluster as subplan
        for child in gr.children:
            if not child.name or not child.name.startswith("cluster"):
                raise GraphError(
                    "subgraphs must be named cluster_* — cluster names "
                    "carry meaning: they become nested harnesses",
                    0)
            parent_name = child.name[len("cluster"):].lstrip("_") or "cluster"
            first_node = (child.nodes[child.order[0]].attrs
                          if child.order else {})
            parent = TaskSpec(
                name=parent_name,
                description=first_node.get(
                    "label", f"nested harness {parent_name}"),
                agent=first_node.get("agent", "executive"),
                subplan=build(child, depth + 1))
            tasks[parent_name] = parent
        # ---- raw-edge resolution (compile time, no phantoms) ----
        # member -> the cluster's parent TaskSpec; member -> child graph
        owner: dict[str, TaskSpec] = {}
        child_of: dict[str, _Graph] = {}
        for child in gr.children:
            parent = tasks[child.name[len("cluster"):].lstrip("_")
                           or "cluster"]
            for n in child.order:
                owner[n] = parent
                child_of[n] = child

        def dep(ta: TaskSpec, tb: TaskSpec) -> None:
            # a -> b means b RUNS AFTER a: b depends on a
            if ta.name != tb.name and ta.name not in tb.depends_on:
                tb.depends_on.append(ta.name)

        for chain, attrs, line in gr.raw_chains:
            if attrs.get("class"):
                raise GraphError(
                    "edges cannot set class — classification lives on "
                    "the node where the agent acts; a stylesheet that "
                    "could move classes could hide danger", line)
            for a, b in zip(chain, chain[1:]):
                ta = tasks.get(a) or owner.get(a)
                tb = tasks.get(b) or owner.get(b)
                if ta is None or tb is None:
                    missing = a if ta is None else b
                    raise GraphError(
                        f"edge names '{missing}' which is never declared "
                        "in this graph — declare every node explicitly "
                        "([agent=...]) or route the edge through its "
                        "cluster", line)
                if a in child_of and b in child_of \
                        and child_of[a] is child_of[b]:
                    # intra-cluster edge declared at the parent level:
                    # it belongs INSIDE the nested harness
                    sub = byname = {t.name: t for t in ta.subplan}
                    if a in sub and b in sub:
                        dep(sub[a], sub[b])
                    continue
                dep(ta, tb)
        _check_cycles(list(tasks.values()))
        out = [tasks[n] for n in tasks]
        if style_map:
            apply_style(out, style_map)
        return out

    tasks = build(g, 0)
    _check_cycles(tasks)
    return tasks


def _check_cycles(tasks: list[TaskSpec]) -> None:
    names = {t.name for t in tasks}
    for t in tasks:
        for d in t.depends_on:
            if d not in names:
                raise GraphError(
                    f"task '{t.name}' depends on '{d}' which is not in "
                    "this graph (cluster edges attach through the parent)")
    from .orchestrator import _find_cycles
    cycles = _find_cycles(tasks)
    if cycles:
        raise GraphError("cycle detected: " + "; ".join(cycles))


# ------------------------------------------------------------------ style


def parse_style(text: str) -> list[tuple[str, dict]]:
    """INI sections matched by fnmatch. Keys: model, agent, profile,
    max_attempts. NOT class — stylesheets route, they never declassify."""
    import configparser
    cp = configparser.ConfigParser()
    try:
        cp.read_string(text)
    except configparser.Error as exc:
        raise GraphError(f"stylesheet is not valid INI: {exc}")
    out = []
    for sec in cp.sections():
        rule = dict(cp.items(sec))
        if "class" in rule:
            raise GraphError(
                f"stylesheet section [{sec}] tries to set class — "
                "REFUSED: stylesheets route, they never declassify "
                "(ADR-052)")
        out.append((sec, rule))
    return out


def apply_style(tasks: list[TaskSpec],
                style_map: list[tuple[str, dict]]) -> int:
    """PER-KEY FALLBACK (the CSS habit): for each key (model, agent,
    max_attempts) a task takes the value from the FIRST matching
    section that defines that key — specific patterns first, [*]
    as the fallback. A task with a subplan also matches by its
    cluster name (cluster_build matches the parent task build).
    Subplans are styled recursively. Returns tasks touched."""
    touched = 0

    def matches(t: TaskSpec):
        names = [t.name]
        if t.subplan:
            names.append(f"cluster_{t.name}")
        return [rule for pat, rule in style_map
                if any(fnmatch.fnmatchcase(n, pat) for n in names)]

    def walk(ts: list[TaskSpec]) -> None:
        nonlocal touched
        for t in ts:
            rules = matches(t)
            if rules:
                touched += 1
                for rule in rules:
                    if "model" in rule:
                        t.model = rule["model"]
                        break
                for rule in rules:
                    if "agent" in rule:
                        t.agent = rule["agent"]
                        break
                for rule in rules:
                    if "max_attempts" in rule:
                        try:
                            t.max_attempts = int(rule["max_attempts"])
                        except ValueError:
                            raise GraphError(
                                "max_attempts must be an integer, got "
                                f"{rule['max_attempts']!r}")
                        break
            if t.subplan:
                walk(t.subplan)

    walk(tasks)
    return touched


# ------------------------------------------------------------------ render


def render_plan(tasks: list[TaskSpec]) -> str:
    lines = ["GRAPH — compiled plan (DOT subset -> TaskSpec)"]

    def walk(ts: list[TaskSpec], indent: str) -> None:
        for t in ts:
            routing = f"  model={t.model}" if t.model else ""
            deps = f"  after {','.join(t.depends_on)}" if t.depends_on else ""
            lines.append(f"{indent}- {t.name} [{t.agent}/"
                         f"{t.action_class.value}{routing}]{deps}")
            if t.subplan:
                lines.append(f"{indent}  subplan (nested harness):")
                walk(t.subplan, indent + "    ")

    walk(tasks, "  ")
    n = len(tasks)

    def count(ts: list[TaskSpec]) -> int:
        return sum(1 + (count(t.subplan) if t.subplan else 0) for t in ts)
    lines.append(f"  {count(tasks)} task(s) total; stylesheets route, "
                 "they never declassify")
    return "\n".join(lines)
