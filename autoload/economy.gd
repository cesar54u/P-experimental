extends Node

var metal: int = 100

func add(amount: int) -> void:
	metal += amount
	EventBus.resources_changed.emit(metal)

func spend(amount: int) -> bool:
	if metal < amount:
		return false
	metal -= amount
	EventBus.resources_changed.emit(metal)
	return true
