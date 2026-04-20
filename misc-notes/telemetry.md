**The most common cause — missing consent file**

OpenVINO telemetry requires user consent during installation. If the control file doesn't exist on the system, telemetry can't initialize properly. This often surfaces as an error rather than silently skipping. The fix is to explicitly opt out (or opt in) so the control file gets created:

```bash
opt_in_out --opt_out
```

or if `opt_in_out` isn't on your PATH (common with venv/portable installs):

```bash
# From your venv or ComfyUI embedded Python
python -m openvino.tools.ovc.telemetry_utils opt_out
```

**The other common cause — version mismatch**

If you installed OpenVINO via pip and the `openvino-telemetry` package version doesn't match the core `openvino` version, you get initialization errors. Check:

```bash
pip show openvino openvino-telemetry
```

Both should be on the same version (currently `2025.2.0`). If they're mismatched:

```bash
pip install openvino openvino-telemetry --upgrade
```

**For your portable ComfyUI setup specifically**, since you're running `python_embeded`, the `opt_in_out` command won't be on the system PATH. You'd run it as:

```bash
.\python_embeded\python.exe -c "from openvino_telemetry.opt_in_out import main; main()" --opt_out
```

---

