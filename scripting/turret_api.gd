class_name TurretAPI extends RefCounted

var turret: Node2D
var aim_target: Node2D = null
var firing: bool = false

func _init(t: Node2D) -> void:
	turret = t

func nearest_enemy() -> Variant:
	var best: Node2D = null
	var best_d := INF
	for e in turret.get_tree().get_nodes_in_group("enemies"):
		var d := turret.global_position.distance_squared_to(e.global_position)
		if d < best_d:
			best_d = d
			best = e
	return best

func distance(t: Node2D) -> float:
	if not is_instance_valid(t):
		return INF
	return turret.global_position.distance_to(t.global_position)

func aim(t: Node2D) -> void:
	aim_target = t

func fire() -> void:
	firing = true

func flush() -> void:
	if aim_target != null and is_instance_valid(aim_target):
		turret.rotation = turret.global_position.angle_to_point(aim_target.global_position)
	if firing:
		turret.shoot()
	aim_target = null
	firing = false

func default_behavior() -> void:
	var t = nearest_enemy()
	if t:
		aim(t)
		fire()
	flush()
