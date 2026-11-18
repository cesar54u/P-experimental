extends Node

signal resources_changed(total: int)
signal build_ordered(builder: Node, scene: PackedScene, pos: Vector2)
signal program_deployed(turret_id: int, ok: bool, message: String)
