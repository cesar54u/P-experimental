class_name CodeConsole extends CanvasLayer

@onready var code_edit: CodeEdit = $Panel/VBox/CodeEdit
@onready var deploy_btn: Button = $Panel/VBox/DeployBtn
@onready var error_label: Label = $Panel/VBox/ErrorLabel

var target_turret: Turret = null

func _ready() -> void:
	EventBus.program_deployed.connect(_on_program_deployed)
	deploy_btn.pressed.connect(_on_deploy_pressed)

func show_for_turret(t: Turret) -> void:
	target_turret = t
	show()

func _on_deploy_pressed() -> void:
	if target_turret == null:
		return
	var cc := get_tree().get_first_node_in_group("command_center") as CommandCenter
	if cc:
		cc.deploy_program(target_turret, code_edit.text)

func _on_program_deployed(turret_id: int, ok: bool, message: String) -> void:
	if target_turret == null or target_turret.id != turret_id:
		return
	if ok:
		error_label.text = "✓ Desplegado"
		error_label.modulate = Color.GREEN
	else:
		error_label.text = "✗ " + message
		error_label.modulate = Color.RED
