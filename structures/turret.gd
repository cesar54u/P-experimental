class_name Turret extends Node2D

static var _next_id: int = 0
var id: int = 0
var program: Variant = null
var api: TurretAPI
var runtime: ScriptRuntime = MiniPyRuntime.new()
@export var instruction_budget: int = 300
@export var think_interval: float = 0.25
@export var bullet_scene: PackedScene
var _acc: float = 0.0

func _ready() -> void:
	id = _next_id
	_next_id += 1
	api = TurretAPI.new(self)
	add_to_group("turrets")

## Instancia una bala en la posición del cañón con la rotación actual.
func shoot() -> void:
	if bullet_scene == null:
		return
	var b := bullet_scene.instantiate()
	b.global_position = global_position
	b.direction = Vector2.RIGHT.rotated(rotation)
	b.damage = 10
	get_tree().current_scene.add_child(b)

func receive_program(p: Variant) -> void:
	program = p

## Llamado cuando el jugador hace clic sobre el ClickArea de la torreta.
func _on_click_area_input_event(_viewport: Node, event: InputEvent, _shape_idx: int) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		var console := get_tree().root.find_child("CodeConsole", true, false)
		if console and console.has_method("show_for_turret"):
			console.show_for_turret(self)

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
