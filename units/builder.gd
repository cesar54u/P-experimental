class_name Builder extends Ship

enum State { IDLE, MOVING, BUILDING }

var state: State = State.IDLE
var _build_timer: float = 0.0
@export var build_time: float = 2.0

func _ready() -> void:
	add_to_group("builders")

func give_order(o: Order) -> void:
	super(o)
	if o.type == Order.Type.BUILD:
		nav.target_position = o.target_pos
		state = State.MOVING

func _physics_process(delta: float) -> void:
	super(delta)
	match state:
		State.MOVING:
			if nav.is_navigation_finished():
				state = State.BUILDING
				_build_timer = 0.0
		State.BUILDING:
			_build_timer += delta
			if _build_timer >= build_time:
				_finish_build()
		State.IDLE:
			order = null

func _finish_build() -> void:
	if order == null or order.type != Order.Type.BUILD:
		state = State.IDLE
		return
	var scene: PackedScene = order.payload.get("scene")
	if scene:
		var instance := scene.instantiate()
		instance.global_position = order.target_pos
		get_tree().root.get_node("Main/World/Structures").add_child(instance)
	order = null
	state = State.IDLE
