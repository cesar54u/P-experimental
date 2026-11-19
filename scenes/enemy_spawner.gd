extends Node2D
## Spawner de enemigos: cada cierto tiempo instancia un enemigo en un borde aleatorio del mapa.

@export var enemy_scene: PackedScene
@export var spawn_interval: float = 5.0
## Tamaño del área de juego para calcular bordes. Ajustar según tu mapa.
@export var map_size: Vector2 = Vector2(1920, 1080)

@onready var timer: Timer = $Timer

func _ready() -> void:
	# Configurar el timer hijo.
	timer.wait_time = spawn_interval
	timer.autostart = true
	timer.timeout.connect(_on_timer_timeout)
	# Iniciar si no tiene autostart habilitado en el editor.
	if not timer.is_stopped():
		pass
	else:
		timer.start()

func _on_timer_timeout() -> void:
	if enemy_scene == null:
		push_warning("EnemySpawner: enemy_scene no asignada.")
		return

	var instance := enemy_scene.instantiate()
	instance.global_position = _random_border_position()

	# Añadir al contenedor Units si existe, si no, al current_scene.
	var units := get_tree().root.find_child("Units", true, false)
	if units:
		units.add_child(instance)
	else:
		get_tree().current_scene.add_child(instance)

## Genera una posición aleatoria en uno de los cuatro bordes del mapa.
func _random_border_position() -> Vector2:
	var edge := randi() % 4
	match edge:
		0: # Borde superior
			return Vector2(randf_range(0, map_size.x), 0)
		1: # Borde inferior
			return Vector2(randf_range(0, map_size.x), map_size.y)
		2: # Borde izquierdo
			return Vector2(0, randf_range(0, map_size.y))
		3: # Borde derecho
			return Vector2(map_size.x, randf_range(0, map_size.y))
	return Vector2.ZERO
