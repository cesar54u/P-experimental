class_name Order extends RefCounted

enum Type { MOVE, MINE, BUILD, ATTACK }

var type: Type
var target_pos: Vector2
var target_node: Node
var payload: Dictionary = {}

static func move(pos: Vector2) -> Order:
	var o := Order.new()
	o.type = Type.MOVE
	o.target_pos = pos
	return o

static func build(pos: Vector2, scene: PackedScene) -> Order:
	var o := Order.new()
	o.type = Type.BUILD
	o.target_pos = pos
	o.payload = {"scene": scene}
	return o

static func attack(target: Node) -> Order:
	var o := Order.new()
	o.type = Type.ATTACK
	o.target_node = target
	return o
