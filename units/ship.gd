class_name Ship extends CharacterBody2D

@export var speed: float = 180.0
@onready var nav: NavigationAgent2D = $NavigationAgent2D

var order: Order = null

func give_order(o: Order) -> void:
	order = o
	if o.type == Order.Type.MOVE:
		nav.target_position = o.target_pos

func _physics_process(_delta: float) -> void:
	if nav.is_navigation_finished():
		velocity = Vector2.ZERO
	else:
		var next := nav.get_next_path_position()
		velocity = global_position.direction_to(next) * speed
	move_and_slide()
