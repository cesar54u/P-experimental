class_name MiniPyRuntime extends ScriptRuntime
## Backend de intérprete Python-like (Fase 4).
## Por ahora retorna error descriptivo; la implementación real va aquí.

func compile(source: String) -> Dictionary:
	if source.strip_edges().is_empty():
		return {"ok": false, "program": null, "error": "Programa vacío"}
	# TODO Fase 4: lexer -> parser -> AST
	return {"ok": false, "program": null, "error": "Intérprete no implementado aún (Fase 4)"}

func run_tick(_program: Variant, _api: TurretAPI, _budget: int) -> Dictionary:
	return {"ok": false, "steps": 0, "error": "Intérprete no implementado aún (Fase 4)"}
