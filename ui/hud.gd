class_name HUD extends Control

@onready var metal_label: Label = $MetalLabel
@onready var build_btn: Button = get_node_or_null("BuildTurretBtn")

var is_placing_turret: bool = false

func _ready() -> void:
	EventBus.resources_changed.connect(_on_resources_changed)
	_on_resources_changed(Economy.metal)
	
	if build_btn:
		build_btn.pressed.connect(_on_build_btn_pressed)

func _on_resources_changed(total: int) -> void:
	metal_label.text = "Metal: %d" % total

func _on_build_btn_pressed() -> void:
	if Economy.metal < 75:
		print("¡No tienes suficiente metal para la torreta (cuesta 75)!")
		return
	is_placing_turret = true
	print("Modo construcción: haz clic izquierdo en el mapa para colocar la torreta (o clic derecho para cancelar).")

func _unhandled_input(event: InputEvent) -> void:
	if is_placing_turret and event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		var pos := get_global_mouse_position()
		var cc := get_tree().get_first_node_in_group("command_center") as CommandCenter
		if cc:
			var success := cc.order_turret(pos)
			if success:
				print("Torreta ordenada con éxito en: ", pos)
			else:
				print("No se pudo construir (verifica si el constructor está ocupado o falta metal)")
		is_placing_turret = false
		get_viewport().set_input_as_handled()
	elif is_placing_turret and event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_RIGHT:
		is_placing_turret = false
		print("Construcción cancelada.")
