class_name Enemy extends CharacterBody2D
## Nave enemiga que navega hacia el CommandCenter y lo ataca.

@export var speed: float = 100.0
@export var hp: int = 30
@export var damage: int = 10
@export var attack_interval: float = 1.0

@onready var nav: NavigationAgent2D = $NavigationAgent2D

var _attack_timer: float = 0.0
var _retarget_timer: float = 0.0
## Intervalo para reasignar destino de navegación (evita hacerlo cada frame).
const RETARGET_INTERVAL: float = 0.5

func _ready() -> void:
	add_to_group("enemies")

func _physics_process(delta: float) -> void:
	var cc := _find_command_center()
	if cc == null:
		# Sin centro de mando: quedarse quieto.
		velocity = Vector2.ZERO
		move_and_slide()
		return

	# Reasignar destino periódicamente, no cada frame.
	_retarget_timer += delta
	if _retarget_timer >= RETARGET_INTERVAL:
		_retarget_timer = 0.0
		nav.target_position = cc.global_position

	# Moverse hacia el objetivo.
	if nav.is_navigation_finished():
		velocity = Vector2.ZERO
	else:
		var next := nav.get_next_path_position()
		velocity = global_position.direction_to(next) * speed
	move_and_slide()

	# Atacar si está a corta distancia.
	if global_position.distance_to(cc.global_position) <= nav.target_desired_distance + 10.0:
		_attack_timer += delta
		if _attack_timer >= attack_interval:
			_attack_timer = 0.0
			cc.take_damage(damage)

## Recibe daño; si llega a 0 se destruye.
func take_damage(amount: int) -> void:
	hp -= amount
	if hp <= 0:
		queue_free()

## Busca el CommandCenter más cercano en el grupo "command_center".
func _find_command_center() -> Node2D:
	var best: Node2D = null
	var best_d := INF
	for cc in get_tree().get_nodes_in_group("command_center"):
		var d := global_position.distance_squared_to(cc.global_position)
		if d < best_d:
			best_d = d
			best = cc
	return best
