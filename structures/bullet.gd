class_name Bullet extends Area2D
## Proyectil que viaja en línea recta y daña enemigos al contacto.

var direction: Vector2 = Vector2.RIGHT
@export var speed: float = 500.0
@export var damage: int = 10
@export var lifetime: float = 3.0

var _age: float = 0.0

func _ready() -> void:
	# Conectar señales para detectar colisiones y salida de pantalla.
	area_entered.connect(_on_area_entered)
	body_entered.connect(_on_body_entered)
	var notifier := get_node_or_null("VisibleOnScreenNotifier2D")
	if notifier:
		notifier.screen_exited.connect(_on_screen_exited)

func _physics_process(delta: float) -> void:
	# Movimiento en línea recta.
	global_position += direction * speed * delta

	# Autodestrucción por tiempo de vida.
	_age += delta
	if _age >= lifetime:
		queue_free()

## Cuando colisiona con un Area2D (ej: otro enemigo tipo Area2D).
func _on_area_entered(area: Area2D) -> void:
	if area.is_in_group("enemies") and area.has_method("take_damage"):
		area.take_damage(damage)
		queue_free()

## Cuando colisiona con un cuerpo físico (CharacterBody2D del enemigo).
func _on_body_entered(body: Node2D) -> void:
	if body.is_in_group("enemies") and body.has_method("take_damage"):
		body.take_damage(damage)
		queue_free()

## Se destruye al salir de la pantalla visible.
func _on_screen_exited() -> void:
	queue_free()
