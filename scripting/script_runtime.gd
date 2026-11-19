class_name ScriptRuntime extends RefCounted

func compile(_source: String) -> Dictionary:
	return {"ok": false, "program": null, "error": "no implementado"}

func run_tick(_program: Variant, _api: Variant, _budget: int) -> Dictionary:
	return {"ok": false, "steps": 0, "error": "no implementado"}
