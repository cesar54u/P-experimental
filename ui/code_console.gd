class_name CodeConsole extends CanvasLayer

@onready var code_edit: CodeEdit = $Panel/VBox/CodeEdit
@onready var deploy_btn: Button = $Panel/VBox/DeployBtn
@onready var error_label: Label = $Panel/VBox/ErrorLabel

var target_turret: Turret = null

func _ready() -> void:
	EventBus.program_deployed.connect(_on_program_deployed)
	deploy_btn.pressed.connect(_on_deploy_pressed)
	# Cerrar con Escape
	set_process_unhandled_key_input(true)

func _unhandled_key_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
		hide()

func show_for_turret(t: Turret) -> void:
	target_turret = t
	error_label.text = "Listo para programar"
	error_label.modulate = Color.WHITE
	show()

func _on_deploy_pressed() -> void:
	if target_turret == null or not is_instance_valid(target_turret):
		error_label.text = "Sin torreta seleccionada"
		error_label.modulate = Color.RED
		return
	var cc := get_tree().get_first_node_in_group("command_center") as CommandCenter
	if cc == null:
		error_label.text = "Sin CommandCenter"
		error_label.modulate = Color.RED
		return
	cc.deploy_program(target_turret, code_edit.text)

func _on_program_deployed(turret_id: int, ok: bool, message: String) -> void:
	if target_turret == null:
		return
	if target_turret.id != turret_id:
		return
	if ok:
		error_label.text = "✓ Desplegado"
		error_label.modulate = Color.GREEN
	else:
		error_label.text = "✗ " + message
		error_label.modulate = Color.RED
