# Custom node development

For new packs, inspect the installed ComfyUI API and the official [V3 migration guide](https://docs.comfy.org/custom-nodes/v3_migration). Use V3 where supported; preserve compatibility when maintaining a V1 pack rather than migrating it as an unrelated change.

## Pack and node contracts

A pack is one directory under `custom_nodes/`. Its `__init__.py` exposes registration, node classes can live in `nodes.py`, and an optional `web/` directory contains frontend extensions. Registry packaging uses `pyproject.toml`; dependency declarations belong in the pack's supported requirements workflow. Use `$python-environment` for interpreter selection, imports, or dependency changes, and avoid duplicating the host's accelerator stack.

A minimal V3 contract is:

```python
from comfy_api.latest import ComfyExtension, io


class InvertImage(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="Example_InvertImage",
            display_name="Invert Image",
            category="example/image",
            inputs=[io.Image.Input("image")],
            outputs=[io.Image.Output()],
        )

    @classmethod
    def execute(cls, image) -> io.NodeOutput:
        return io.NodeOutput(1.0 - image)


class ExampleExtension(ComfyExtension):
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [InvertImage]


async def comfy_entrypoint() -> ExampleExtension:
    return ExampleExtension()
```

Place or re-export `comfy_entrypoint` at the pack root. Input ids match `execute` argument names; return values follow output-schema order. Saved workflows identify nodes by `node_id`, so keep that id stable and change `display_name` for a cosmetic rename.

IMAGE tensors conventionally use `[batch, height, width, channels]` floating values in 0..1; MASK uses `[batch, height, width]`. LATENT is a mapping containing `samples`, but spatial scaling and channel count depend on the model family. Preserve batch and device semantics rather than assuming every latent is an image-family H/8 tensor.

Useful V3 schema features include lazy inputs, `validate_inputs`, `fingerprint_inputs`, `check_lazy_status`, dynamic combos, autogrow inputs, and output-node flags. Choose cache behavior for the actual operation; do not mark deterministic work non-idempotent merely to bypass a stale-output problem. Use the installed `ui.PreviewImage` or save helpers when a preview/output is required; their `cls` context preserves workflow metadata.

With frontend extensions, expose `WEB_DIRECTORY` and register a uniquely named extension. Keep serialized widget values ordinary JSON scalars so workflows remain portable.

## Verify registration and behavior

Syntax compilation catches syntax only. Import the pack using the selected ComfyUI environment from its installation root; an import failure in an unrelated Python environment is not evidence that the pack is broken.

Restart when needed to load a new pack, inspect its startup result, and confirm the exact node id in `/object_info` or `nodes show`. Run the smallest graph that exercises the changed behavior, including a terminal output when necessary. Import success alone does not establish registration or execution.

A repository cloned under `custom_nodes/` is not automatically a node pack. Verify its V1 `NODE_CLASS_MAPPINGS` or V3 entrypoint/node list before packaging it as one; some source setups place research libraries there only for editable installation.

## Compatibility and publishing

V1 schemas use `INPUT_TYPES`, `RETURN_TYPES`, `FUNCTION`, and `NODE_CLASS_MAPPINGS`; V3 uses `define_schema`, typed outputs, `execute`, and `ComfyExtension.get_node_list`. Keep old workflow identities during an intentional migration, or register an explicit node replacement through the extension lifecycle. Constructing a replacement object without registering it does nothing.

The official [registry publishing guide](https://docs.comfy.org/registry/publishing) defines the current metadata and upload procedure. `comfy node init` initializes metadata, not the implementation. Before an authorized publish, review what will be included, confirm the publisher/version, and keep tokens out of Git and command logs. Do not assume the host's Python packages or untracked files will travel with the pack.
