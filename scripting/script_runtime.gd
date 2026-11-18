class_name ScriptRuntime extends RefCounted

## Compila el código fuente del jugador.
## Retorna: {ok: bool, program: Variant, error: String}
func compile(_source: String) -> Dictionary:
	return {"ok": false, "program": null, "error": "no implementado"}

## Ejecuta un tick con presupuesto de instrucciones.
## Retorna: {ok: bool, steps: int, error: String}
func run_tick(_program: Variant, _api: TurretAPI, _budget: int) -> Dictionary:
	return {"ok": false, "steps": 0, "error": "no implementado"}
