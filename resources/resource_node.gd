class_name ResourceNode extends Area2D

@export var amount: int = 500

func extract(n: int) -> int:
	var taken: int = mini(n, amount)
	amount -= taken
	if amount <= 0:
		queue_free()
	return taken
