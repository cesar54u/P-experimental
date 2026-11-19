extends Node2D

@export var enemy_scene: PackedScene
@export var spawn_interval: float = 8.0
@export var map_size: Vector2 = Vector2(1152, 648)

var _timer: float = 0.0

func _process(delta: float) -> void:
	if enemy_scene == null:
		return
	_timer += delta
	if _timer >= spawn_interval:
		_timer = 0.0
		_spawn()

func _spawn() -> void:
	# Elegir un lado aleatorio: 0=arriba, 1=abajo, 2=izquierda, 3=derecha
	var side := randi() % 4
	var pos := Vector2.ZERO
	match side:
		0: pos = Vector2(randf_range(0, map_size.x), 0)
		1: pos = Vector2(randf_range(0, map_size.x), map_size.y)
		2: pos = Vector2(0, randf_range(0, map_size.y))
		3: pos = Vector2(map_size.x, randf_range(0, map_size.y))

	var e := enemy_scene.instantiate()
	# Añadir al padre del spawner para que esté en la escena principal
	get_parent().add_child(e)
	e.global_position = pos
