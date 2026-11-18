class_name Turret extends Node2D

static var _next_id: int = 0
var id: int = 0
var program: Variant = null
var api: TurretAPI
var runtime: ScriptRuntime = MiniPyRuntime.new()
@export var instruction_budget: int = 300
@export var think_interval: float = 0.25
var _acc: float = 0.0

func _ready() -> void:
	id = _next_id
	_next_id += 1
	api = TurretAPI.new(self)
	add_to_group("turrets")

func receive_program(p: Variant) -> void:
	program = p

func _physics_process(delta: float) -> void:
	_acc += delta
	if _acc < think_interval:
		return
	_acc = 0.0
	if program == null:
		api.default_behavior()
		return
	var r := runtime.run_tick(program, api, instruction_budget)
	if not r.ok:
		program = null
		EventBus.program_deployed.emit(id, false, r.error)
