class_name HUD extends Control

@onready var metal_label: Label = $MetalLabel

func _ready() -> void:
	EventBus.resources_changed.connect(_on_resources_changed)
	_on_resources_changed(Economy.metal)

func _on_resources_changed(total: int) -> void:
	metal_label.text = "Metal: %d" % total
