extends SceneTree


func _initialize() -> void:
	var arguments := OS.get_cmdline_user_args()
	if arguments.size() != 1:
		quit(1)
		return
	var packer := PCKPacker.new()
	var result := packer.pck_start(arguments[0])
	if result == OK:
		result = packer.add_file("res://localisation/translations.csv", "res://localisation/translations.csv")
	if result == OK:
		result = packer.flush()
	quit(0 if result == OK else 1)
