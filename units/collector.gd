class_name Collector extends Ship

enum State { IDLE, TO_RESOURCE, MINING, RETURNING }

@export var capacity: int = 50
@export var mine_rate: int = 10
var state: State = State.IDLE
var cargo: int = 0
var target: ResourceNode
var _mine_timer: float = 0.0

func _ready() -> void:
	add_to_group("collectors")

func _physics_process(delta: float) -> void:
	super(delta)
	match state:
		State.IDLE:
			target = _find_nearest_resource()
			if target:
				nav.target_position = target.global_position
				state = State.TO_RESOURCE
		State.TO_RESOURCE:
			if not is_instance_valid(target):
				state = State.IDLE
			elif nav.is_navigation_finished():
				state = State.MINING
		State.MINING:
			_mine_timer += delta
			if _mine_timer >= 1.0 and is_instance_valid(target):
				_mine_timer = 0.0
				cargo += target.extract(mine_rate)
			if cargo >= capacity or not is_instance_valid(target):
				nav.target_position = _base_position()
				state = State.RETURNING
		State.RETURNING:
			if nav.is_navigation_finished():
				Economy.add(cargo)
				cargo = 0
				state = State.IDLE

func _find_nearest_resource() -> ResourceNode:
	var best: ResourceNode = null
	var best_d := INF
	for r in get_tree().get_nodes_in_group("resource"):
		var d := global_position.distance_squared_to(r.global_position)
		if d < best_d:
			best_d = d
			best = r
	return best

func _base_position() -> Vector2:
	var cc := get_tree().get_first_node_in_group("command_center")
	if cc:
		return cc.global_position
	return Vector2.ZERO
