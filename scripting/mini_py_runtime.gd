class_name MiniPyRuntime extends RefCounted

# Interprete Python-like para torretas.
# Soporta: def on_tick(), variables, if/elif/else,
#          llamadas a API, comparaciones y aritmetica basica.

const TK_NAME    = "NAME"
const TK_NUMBER  = "NUMBER"
const TK_STRING  = "STRING"
const TK_OP      = "OP"
const TK_NEWLINE = "NEWLINE"
const TK_INDENT  = "INDENT"
const TK_DEDENT  = "DEDENT"
const TK_EOF     = "EOF"

# Estado del parser (se reinicia en cada llamada a _parse)
var _pos := 0
var _tok : Array = []

# ──────────────────────── COMPILE ───────────────────────────────────────────

func compile(source: String) -> Dictionary:
	if source.strip_edges().is_empty():
		return {ok=false, program=null, error="Programa vacio"}
	var tokens := _tokenize(source)
	if tokens.is_empty():
		return {ok=false, program=null, error="No se pudo leer el codigo"}
	var ast := _parse(tokens)
	if ast.has("error"):
		return {ok=false, program=null, error=ast.error}
	for node in ast.body:
		if node.type == "FuncDef" and node.name == "on_tick":
			return {ok=true, program=node, error=""}
	return {ok=false, program=null, error="Falta 'def on_tick():' en el codigo"}

# ──────────────────────── RUN TICK ──────────────────────────────────────────

func run_tick(program: Variant, api: Variant, budget: int) -> Dictionary:
	var ctx := {"vars": {}, "api": api, "steps": 0, "budget": budget}
	var result := _exec_block(program.body, ctx)
	api.flush()
	if result.has("error"):
		return {ok=false, steps=ctx.steps, error=result.error}
	return {ok=true, steps=ctx.steps, error=""}

# ──────────────────────── TOKENIZER ─────────────────────────────────────────

func _tokenize(src: String) -> Array:
	var tokens := []
	var lines := src.split("\n")
	var indent_stack := [0]

	for raw_line in lines:
		var stripped := raw_line.strip_edges()
		if stripped.is_empty() or stripped.begins_with("#"):
			continue
		# Medir indentacion
		var indent := 0
		for ch in raw_line:
			if ch == " ":
				indent += 1
			elif ch == "\t":
				indent += 4
			else:
				break
		var cur_indent: int = indent_stack.back()
		if indent > cur_indent:
			tokens.append({type=TK_INDENT, val=""})
			indent_stack.append(indent)
		while indent < indent_stack.back():
			indent_stack.pop_back()
			tokens.append({type=TK_DEDENT, val=""})
		tokens.append_array(_tokenize_line(stripped))
		tokens.append({type=TK_NEWLINE, val=""})

	while indent_stack.size() > 1:
		indent_stack.pop_back()
		tokens.append({type=TK_DEDENT, val=""})
	tokens.append({type=TK_EOF, val=""})
	return tokens

func _tokenize_line(line: String) -> Array:
	var tokens := []
	var i := 0
	var keywords := ["not","and","or","if","elif","else","def","return","while"]
	while i < line.length():
		var c := line[i]
		if c == " " or c == "\t":
			i += 1
			continue
		if c == "#":
			break
		# String literal
		if c == '"' or c == "'":
			var q := c
			var s := ""
			i += 1
			while i < line.length() and line[i] != q:
				s += line[i]
				i += 1
			i += 1
			tokens.append({type=TK_STRING, val=s})
			continue
		# Numero
		if c.is_valid_int() or (c == "-" and i + 1 < line.length() and line[i + 1].is_valid_int()):
			var num := c
			i += 1
			while i < line.length() and (line[i].is_valid_int() or line[i] == "."):
				num += line[i]
				i += 1
			tokens.append({type=TK_NUMBER, val=float(num)})
			continue
		# Nombre o palabra clave
		if c.is_valid_identifier() or c == "_":
			var name := ""
			while i < line.length() and (line[i].is_valid_identifier() or line[i] == "_"):
				name += line[i]
				i += 1
			if name in keywords:
				tokens.append({type=TK_OP, val=name})
			elif name == "True":
				tokens.append({type=TK_NUMBER, val=1.0})
			elif name == "False" or name == "None":
				tokens.append({type=TK_NUMBER, val=0.0})
			else:
				tokens.append({type=TK_NAME, val=name})
			continue
		# Operadores de dos caracteres
		if i + 1 < line.length():
			var two := line.substr(i, 2)
			if two == "==" or two == "!=" or two == "<=" or two == ">=":
				tokens.append({type=TK_OP, val=two})
				i += 2
				continue
		# Operador de un caracter
		if c == "=" or c == "+" or c == "-" or c == "*" or c == "/" or c == "%" \
				or c == "(" or c == ")" or c == "," or c == ":" or c == "<" \
				or c == ">" or c == ".":
			tokens.append({type=TK_OP, val=c})
			i += 1
			continue
		i += 1
	return tokens

# ──────────────────────── PARSER ────────────────────────────────────────────

func _peek() -> Dictionary:
	if _pos < _tok.size():
		return _tok[_pos]
	return {type=TK_EOF, val=""}

func _consume(_expected: String = "") -> Dictionary:
	var t := _peek()
	_pos += 1
	return t

func _skip_newlines() -> void:
	while _peek().type == TK_NEWLINE:
		_pos += 1

func _parse(tokens: Array) -> Dictionary:
	_tok = tokens
	_pos = 0
	var body := []
	_skip_newlines()
	while _peek().type != TK_EOF:
		var stmt := _parse_stmt()
		if stmt.has("error"):
			return stmt
		body.append(stmt)
		_skip_newlines()
	return {type="Module", body=body}

func _parse_stmt() -> Dictionary:
	var t := _peek()
	if t.type == TK_OP and t.val == "def":
		return _parse_funcdef()
	if t.type == TK_OP and (t.val == "if" or t.val == "elif" or t.val == "else"):
		return _parse_if()
	if t.type == TK_OP and t.val == "return":
		_consume()
		if _peek().type == TK_NEWLINE or _peek().type == TK_EOF:
			return {type="Return", value=null}
		return {type="Return", value=_parse_expr()}
	if t.type == TK_NAME:
		var name := t.val
		_consume()
		if _peek().type == TK_OP and _peek().val == "=":
			_consume()
			return {type="Assign", target=name, value=_parse_expr()}
		if _peek().type == TK_OP and _peek().val == "(":
			return {type="ExprStmt", expr=_parse_call_rest(name)}
		if _peek().type == TK_OP and _peek().val == ".":
			_consume()
			var attr := _consume(TK_NAME).val
			if _peek().type == TK_OP and _peek().val == "(":
				return {type="ExprStmt", expr=_parse_call_rest(name + "." + attr)}
			return {type="ExprStmt", expr={type="Attr", obj=name, attr=attr}}
		return {type="ExprStmt", expr={type="Name", val=name}}
	# Ignorar lineas desconocidas
	while _peek().type != TK_NEWLINE and _peek().type != TK_EOF:
		_consume()
	return {type="Noop"}

func _parse_funcdef() -> Dictionary:
	_consume()  # def
	var name := _consume(TK_NAME).val
	_consume()  # (
	_consume()  # )
	_consume()  # :
	_skip_newlines()
	var block := _parse_indented_block()
	if block.has("error"):
		return block
	return {type="FuncDef", name=name, body=block.stmts}

func _parse_if() -> Dictionary:
	var kw := _consume().val
	var test = null
	if kw != "else":
		test = _parse_expr()
		_consume()  # :
	else:
		if _peek().type == TK_OP and _peek().val == ":":
			_consume()
	_skip_newlines()
	var block := _parse_indented_block()
	if block.has("error"):
		return block
	var orelse := []
	_skip_newlines()
	if _peek().type == TK_OP and (_peek().val == "elif" or _peek().val == "else"):
		var alt := _parse_if()
		if alt.has("error"):
			return alt
		orelse = [alt]
	return {type="If", test=test, body=block.stmts, orelse=orelse}

func _parse_indented_block() -> Dictionary:
	if _peek().type != TK_INDENT:
		return {error="Se esperaba bloque indentado (verifica sangria)"}
	_consume()  # INDENT
	var stmts := []
	_skip_newlines()
	while _peek().type != TK_DEDENT and _peek().type != TK_EOF:
		var s := _parse_stmt()
		if s.has("error"):
			return s
		stmts.append(s)
		_skip_newlines()
	if _peek().type == TK_DEDENT:
		_consume()
	return {stmts=stmts}

func _parse_expr() -> Dictionary:
	return _parse_or()

func _parse_or() -> Dictionary:
	var left := _parse_and()
	while _peek().type == TK_OP and _peek().val == "or":
		_consume()
		left = {type="BinOp", op="or", left=left, right=_parse_and()}
	return left

func _parse_and() -> Dictionary:
	var left := _parse_not()
	while _peek().type == TK_OP and _peek().val == "and":
		_consume()
		left = {type="BinOp", op="and", left=left, right=_parse_not()}
	return left

func _parse_not() -> Dictionary:
	if _peek().type == TK_OP and _peek().val == "not":
		_consume()
		return {type="UnaryOp", op="not", val=_parse_comparison()}
	return _parse_comparison()

func _parse_comparison() -> Dictionary:
	var left := _parse_add()
	while _peek().type == TK_OP:
		var v := _peek().val
		if v == "==" or v == "!=" or v == "<" or v == ">" or v == "<=" or v == ">=":
			var op := _consume().val
			left = {type="BinOp", op=op, left=left, right=_parse_add()}
		else:
			break
	return left

func _parse_add() -> Dictionary:
	var left := _parse_mul()
	while _peek().type == TK_OP and (_peek().val == "+" or _peek().val == "-"):
		var op := _consume().val
		left = {type="BinOp", op=op, left=left, right=_parse_mul()}
	return left

func _parse_mul() -> Dictionary:
	var left := _parse_atom()
	while _peek().type == TK_OP and (_peek().val == "*" or _peek().val == "/" or _peek().val == "%"):
		var op := _consume().val
		left = {type="BinOp", op=op, left=left, right=_parse_atom()}
	return left

func _parse_atom() -> Dictionary:
	var t := _peek()
	if t.type == TK_NUMBER:
		_consume()
		return {type="Num", val=t.val}
	if t.type == TK_STRING:
		_consume()
		return {type="Str", val=t.val}
	if t.type == TK_NAME:
		var name := t.val
		_consume()
		if _peek().type == TK_OP and _peek().val == "(":
			return _parse_call_rest(name)
		if _peek().type == TK_OP and _peek().val == ".":
			_consume()
			var attr := _consume(TK_NAME).val
			if _peek().type == TK_OP and _peek().val == "(":
				return _parse_call_rest(name + "." + attr)
			return {type="Attr", obj=name, attr=attr}
		return {type="Name", val=name}
	if t.type == TK_OP and t.val == "(":
		_consume()
		var e := _parse_expr()
		_consume()
		return e
	if t.type == TK_OP and t.val == "-":
		_consume()
		return {type="UnaryOp", op="-", val=_parse_atom()}
	return {type="Num", val=0.0}

func _parse_call_rest(func_name: String) -> Dictionary:
	_consume()  # (
	var args := []
	while not (_peek().type == TK_OP and _peek().val == ")"):
		args.append(_parse_expr())
		if _peek().type == TK_OP and _peek().val == ",":
			_consume()
		if _peek().type == TK_NEWLINE or _peek().type == TK_EOF:
			break
	if _peek().type == TK_OP and _peek().val == ")":
		_consume()
	return {type="Call", func=func_name, args=args}

# ──────────────────────── EXECUTOR ──────────────────────────────────────────

func _exec_block(stmts: Array, ctx: Dictionary) -> Dictionary:
	for stmt in stmts:
		ctx.steps += 1
		if ctx.steps > ctx.budget:
			return {error="Limite de instrucciones alcanzado"}
		var r := _exec_stmt(stmt, ctx)
		if r.has("error") or r.has("return"):
			return r
	return {}

func _exec_stmt(node: Dictionary, ctx: Dictionary) -> Dictionary:
	match node.type:
		"Assign":
			var v = _eval(node.value, ctx)
			if v is Dictionary and v.has("error"):
				return v
			ctx.vars[node.target] = v
		"ExprStmt":
			var v = _eval(node.expr, ctx)
			if v is Dictionary and v.has("error"):
				return v
		"If":
			var test = _eval(node.test, ctx)
			if test is Dictionary and test.has("error"):
				return test
			if _truthy(test):
				return _exec_block(node.body, ctx)
			elif node.orelse.size() > 0:
				return _exec_block(node.orelse, ctx)
		"Return":
			var v = null
			if node.value != null:
				v = _eval(node.value, ctx)
				if v is Dictionary and v.has("error"):
					return v
			return {"return": v}
		"Noop", "FuncDef":
			pass
	return {}

func _eval(node: Dictionary, ctx: Dictionary) -> Variant:
	match node.type:
		"Num":
			return node.val
		"Str":
			return node.val
		"Name":
			return ctx.vars.get(node.val, null)
		"BinOp":
			var l = _eval(node.left, ctx)
			var r = _eval(node.right, ctx)
			if l is Dictionary and l.has("error"):
				return l
			if r is Dictionary and r.has("error"):
				return r
			match node.op:
				"+":   return _num(l) + _num(r)
				"-":   return _num(l) - _num(r)
				"*":   return _num(l) * _num(r)
				"/":   return 0.0 if _num(r) == 0 else _num(l) / _num(r)
				"%":   return float(int(_num(l)) % int(_num(r)))
				"==":  return 1.0 if l == r else 0.0
				"!=":  return 1.0 if l != r else 0.0
				"<":   return 1.0 if _num(l) < _num(r) else 0.0
				">":   return 1.0 if _num(l) > _num(r) else 0.0
				"<=":  return 1.0 if _num(l) <= _num(r) else 0.0
				">=":  return 1.0 if _num(l) >= _num(r) else 0.0
				"and": return l if not _truthy(l) else r
				"or":  return l if _truthy(l) else r
		"UnaryOp":
			var v = _eval(node.val, ctx)
			match node.op:
				"not": return 1.0 if not _truthy(v) else 0.0
				"-":   return -_num(v)
		"Call":
			return _call(node.func, node.args, ctx)
	return null

func _call(func_name: String, arg_nodes: Array, ctx: Dictionary) -> Variant:
	var api = ctx.api
	var args := []
	for a in arg_nodes:
		args.append(_eval(a, ctx))
	match func_name:
		"nearest_enemy":
			return api.nearest_enemy()
		"distance":
			if args.size() > 0 and args[0] != null:
				return api.distance(args[0])
			return INF
		"aim":
			if args.size() > 0 and args[0] != null:
				api.aim(args[0])
		"fire":
			api.fire()
		_:
			pass
	return null

func _truthy(val: Variant) -> bool:
	if val == null:
		return false
	if val is float or val is int:
		return val != 0.0
	if val is String:
		return val != ""
	return true

func _num(val: Variant) -> float:
	if val == null:
		return 0.0
	if val is float or val is int:
		return float(val)
	return 0.0
