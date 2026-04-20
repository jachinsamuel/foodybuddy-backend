from flask import request, jsonify
import math
import re

def register_calculator_routes(app):
    @app.route("/calculate", methods=["POST"])
    def calculate():
        """Calculate arithmetic expression safely."""
        data = request.json
        expression = data.get("expression", "").strip()
        
        if not expression:
            return jsonify({"error": "No expression provided"}), 400
        
        try:
            result = safe_calculate(expression)
            return jsonify({"result": result, "expression": expression}), 200
        except ZeroDivisionError:
            return jsonify({"error": "Division by zero"}), 400
        except Exception as e:
            return jsonify({"error": f"Invalid expression: {str(e)}"}), 400

    @app.route("/voice", methods=["POST"])
    def voice_parse():
        """Parse voice transcript to math expression."""
        data = request.json
        transcript = data.get("transcript", "").lower().strip()
        
        if not transcript:
            return jsonify({"error": "No transcript provided"}), 400
        
        # Word to number/operator mapping
        replacements = {
            "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
            "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
            "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13",
            "fourteen": "14", "fifteen": "15", "sixteen": "16", "seventeen": "17",
            "eighteen": "18", "nineteen": "19", "twenty": "20", "thirty": "30",
            "forty": "40", "fifty": "50", "sixty": "60", "seventy": "70",
            "eighty": "80", "ninety": "90", "hundred": "*100",
            "plus": "+", "add": "+", "and": "+", "added to": "+",
            "minus": "-", "subtract": "-", "take away": "-", "less": "-",
            "times": "*", "multiplied by": "*", "into": "*", "multiply": "*", "x": "*",
            "divided by": "/", "divide": "/", "over": "/",
            "percent": "/100", "point": ".", "equals": "", "equal": "",
            "calculate": "", "what is": "", "compute": ""
        }
        
        expr = transcript
        for word, symbol in replacements.items():
            expr = re.sub(r"\b" + re.escape(word) + r"\b", symbol, expr)
        
        # Clean up spaces around operators
        expr = re.sub(r"\s+", "", expr)
        expr = re.sub(r"[^0-9+\-*/.()%]", "", expr)
        
        if not expr:
            return jsonify({
                "error": "Could not parse voice input",
                "transcript": transcript
            }), 400
        
        try:
            result = safe_calculate(expr)
            return jsonify({
                "expression": expr,
                "result": result,
                "transcript": transcript
            }), 200
        except Exception as e:
            return jsonify({
                "error": f"Could not calculate: {str(e)}",
                "expression": expr,
                "transcript": transcript
            }), 400


def safe_calculate(expression):
    """Safely evaluate arithmetic expressions."""
    # Clean the expression
    expression = expression.strip().replace(" ", "")
    
    # Allow only safe characters
    if not re.match(r"^[\d+\-*/().%\s]+$", expression):
        raise ValueError("Invalid characters in expression")
    
    # Evaluate safely with restricted builtins
    result = eval(expression, {"__builtins__": {}}, {
        "abs": abs, "round": round,
        "sqrt": math.sqrt, "pi": math.pi
    })
    
    # Format result
    if isinstance(result, float) and result.is_integer():
        return int(result)
    if isinstance(result, float):
        return round(result, 10)
    return result
