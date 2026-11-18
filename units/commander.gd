class_name Commander extends Ship

@export var command_radius: float = 400.0
@onready var command_area: Area2D = $CommandArea

func _ready() -> void:
	add_to_group("commander")
	var shape := CircleShape2D.new()
	shape.radius = command_radius
	var col := CollisionShape2D.new()
	col.shape = shape
	command_area.add_child(col)

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		give_order(Order.move(get_global_mouse_position()))

func units_in_range() -> Array:
	return command_area.get_overlapping_bodies()
