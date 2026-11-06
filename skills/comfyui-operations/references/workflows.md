# Workflow authoring and reuse

Use this reference for graph construction, UI/API conversion, reusable sources, and concurrent canvas edits. CLI version and discovery conventions are in [cli.md](cli.md).

## Distinguish the two formats

An editing-format workflow has `nodes`, `links`, widget values, and potentially subgraph definitions. An API prompt maps node ids to `class_type` and `inputs`; a connection is `[source_node_id, output_index]`. Both may be embedded in a generated PNG, and one is not interchangeable with the other.

The CLI converts UI workflows client-side using the target's `object_info`; there is no server conversion endpoint to assume. Preview and validate before a real submission:

```bash
comfy run --workflow workflow.json --where local --print-prompt
comfy --json workflow validate --workflow api.json --where local
```

`--print-prompt` produces the graph without submitting it. Schema validation checks structure, types, and enums, not model integrity, accelerator compatibility, or image quality. Comfy developer-platform `deploy run` requires API format explicitly; ordinary `run` supports conversion when the target catalog is available.

## Choose a representation by the edit

| Task | Representation |
| --- | --- |
| Small value change to an existing workflow | Discover `workflow slots`, then use `set-slot` or `vary`. |
| Reusable graph or live canvas mutation | Typed structured operations and parameterized recipes, using `workflow apply` / `capture`. |
| Existing headless fragment/blueprint project | Retain its source and recompile with `compose`; this legacy path emits API artifacts, not mergeable canvas operations. |
| Simple independent API prompt with no reusable source | Direct JSON is workable; preserve links and validate against the actual target. |

Templates supply working wiring and widget values, not a universal model recommendation. Fetch a matching template and inspect its slots and node schemas before choosing model files or changing parameters. Avoid regenerating a whole document when the user is concurrently editing its canvas.

For scalar edits, slot addresses are node ids plus input names, not display titles. Subgraph interiors may use `<instance>/<inner>.<input>`; copy the address the CLI actually reports. `workflow vary` zips slot lists and requires matching lengths; it does not take their Cartesian product.

## Structured operations and recipes

`add-node`, `connect`, `set-widget`, `delete-node`, and `apply` validate ordinary edits against `object_info` and return replayable operations. Batch related changes with aliases so newly minted random ids do not need to be guessed:

```json
[
  {"op": "add_node", "class_type": "CheckpointLoaderSimple", "as": "checkpoint"},
  {"op": "add_node", "class_type": "KSampler", "as": "sampler"},
  {"op": "connect", "from": "checkpoint.MODEL", "to": "sampler.model"},
  {"op": "set_widget", "node": "sampler", "widget": "steps", "value": 30}
]
```

```bash
comfy --json workflow apply draft.json --ops ops.json --where local
```

This illustrates one edit batch, not a complete generation graph. `data.aliases` and `data.ops` identify what was created; do not assume small sequential ids. Widget addresses use names, while connection slots can use schema names or indices. `workflow slots` lists widgets, not every connection socket.

Operations carry identity and ordering information (`op_id`, `actor`, `base_version`, `stamp`) for merge-aware consumers. A whole-document `compose` result does not carry equivalent operations. `insert-workflow` is a special emit-only operation: the CLI checks JSON shape, while the server applier performs semantic checks and id remapping. Its emission is not proof that the insert was accepted.

`delete-node` removes a node in a graph; `workflow delete` deletes an account's saved cloud workflow. Verify which resource is being removed.

For reuse, capture a working graph with the widgets that should become named parameters:

```bash
comfy --json workflow capture draft.json --name portrait --param 6.text=positive --param 3.seed=seed -o portrait.recipe.json --where local
comfy --json workflow apply next.json --ops portrait.recipe.json --param positive='a fox' --param seed=42 --where local
```

The numeric addresses above are examples; discover the real ones first. Recipe `${parameter}` holes retain scalar types when they occupy a whole value. Missing required parameters, unknown parameters, and wrong types are errors. Capture can omit unchanged defaults unless parameterized; it also skips canvas-only decoration, splices reroute/get/set links, and promotes primitive values. A captured executable recipe is not a visual round-trip of every note or layout detail.

In a legacy fragment project, derive fragments from a working workflow with `decompose` where possible. It retains working widget types and wiring while lifting loaders, outputs, and scalar parameters. Edit fragments and blueprints, then recompose; do not patch a compiled artifact and leave the reusable source inconsistent. Use recipes for new canvas-native reuse.

## Model and compound-input wiring

Discover model filenames from the selected target and confirm them in the loader's live enum choices. A LoRA's modified MODEL feeds sampling and its modified CLIP feeds both positive and negative text encoders. Check the model family, latent construction, and VAE as a connected graph.

Dynamic combo schemas may expose empty choices because options resolve at runtime. Inspect a current provider template and the selected option's schema instead of declaring the input unsupported. API inputs use flat dotted keys, such as `model.resolution`, not an arbitrary nested object. Autogrow inputs require one flattened key per connection, such as `images.image0` and `images.image1`; a bare `images` link can be invalid. Follow the schema's `wire_as` form and preserve enum types, including string-valued numeric choices.

## Project assets and multi-stage work

The CLI's `project/1` convention uses `comfy.yaml`, `assets/`, `fragments/`, `blueprints/`, `outputs/`, and machine-managed `.comfy/` state. Use `project init` only when introducing that convention and `project status` to inspect an existing project. Keep final outputs in a durable project location rather than losing them in scratch storage.

`assets push` uploads changed assets and records their hash, server name, and backend in `.comfy/assets.lock.json`. It is an external file transfer when targeting cloud; inspect the files before authorizing it. In legacy blueprints:

| Whole-value reference | Meaning |
| --- | --- |
| `$alias.output` | A prior step's output connection. |
| `$item.field` | A `foreach` item's scalar or input. |
| `$asset.relative/path` | A pushed asset resolved through its lock entry. |
| `$var.name` | A scalar from the project's `vars` mapping. |

These references do not interpolate inside surrounding prose. A changed asset can cause `asset_stale`; a missing push causes `asset_not_pushed`. Resolve the transfer deliberately, then recompile. Keep `.comfy/` journals and locks machine-managed; add a human decision log only for decisions they do not capture, such as rejecting a take or changing the canonical reference.

Use one graph for stages that can share loaders, references, and in-server outputs without a review boundary. Use separate jobs when intermediate approval, different backends, memory isolation, or independent retries justify the handoff. Neither graph structure alone nor a CLI feature guarantees simultaneous GPU execution.

For variations, use the supported recipe `foreach` or existing blueprint mechanism. Legacy `compose` chunking returns `written[]` and `out: null`; read the actual returned paths. Match outputs by `outputs_by_item` or node id, never array order. Split paid video shots deliberately when independent failure recovery and human review matter; wait on the submitted ids rather than creating a second polling scheduler.
