class_name CommandCenter extends Node2D

@export var uplink_radius: float = 600.0
@export var turret_scene: PackedScene
@export var turret_cost: int = 75
@export var hp: int = 200

var runtime: ScriptRuntime = MiniPyRuntime.new()

func _ready() -> void:
	add_to_group("command_center")

## Recibe daño de enemigos; al llegar a 0 se pausa el juego.
func take_damage(amount: int) -> void:
	hp -= amount
	if hp <= 0:
		hp = 0
		print("GAME OVER")
		get_tree().paused = true

func order_turret(pos: Vector2) -> bool:
	var builder := _find_idle_builder()
	if builder == null or not Economy.spend(turret_cost):
		return false
	var o := Order.build(pos, turret_scene)
	builder.give_order(o)
	return true

func deploy_program(turret: Turret, source: String) -> void:
	var result: Dictionary = runtime.compile(source)
	if not result.ok:
		EventBus.program_deployed.emit(turret.id, false, result.error)
		return
	if global_position.distance_to(turret.global_position) > uplink_radius:
		EventBus.program_deployed.emit(turret.id, false, "Fuera de alcance")
		return
	turret.receive_program(result.program)
	EventBus.program_deployed.emit(turret.id, true, "OK")

func _find_idle_builder() -> Ship:
	for b in get_tree().get_nodes_in_group("builders"):
		if b.order == null:
			return b
	return null
