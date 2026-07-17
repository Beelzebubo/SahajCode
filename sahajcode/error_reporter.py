"""
SahajCode Error Reporter
Generates bilingual (Nepali/English) error messages with source-line mapping.
"""

from typing import List, Tuple, Optional


class ErrorReporter:
    """Formats and reports errors in both Nepali and English."""
    
    def __init__(self):
        self.errors: List[Tuple[str, str, int, str, str]] = []  # (nepali, english, line, source, suggestion)
    
    def add_error(self, nepali: str, english: str, line: int, source: str = "", suggestion: str = "", caret: Optional[str] = None):
        """Add an error to the report. `caret` is an optional pointer string.
        `nepali`/`english` are used as-is; pass already-prefixed text if desired.
        `source` is the offending line text and `caret` an optional pointer.
        """
        self.errors.append((nepali, english, line, source, suggestion, caret))
    
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    def format_report(self) -> str:
        """Format all errors as a bilingual report."""
        if not self.errors:
            return ""
        
        lines = []
        for nepali, english, line, source, suggestion, caret in self.errors:
            lines.append(nepali)
            lines.append(english)
            if source:
                lines.append(f"          {source}")
                if caret is not None:
                    lines.append(f"          {caret}")
                else:
                    lines.append(f"          {'^' * len(source)}")
            if suggestion:
                lines.append(f"          {suggestion}")
            lines.append("")
        
        return '\n'.join(lines)
    
    def clear(self):
        self.errors.clear()


def format_error(level: str, message_nepali: str, message_english: str, 
                 line: int, source: str = "", suggestion: str = "") -> str:
    """Format a single error message."""
    formatted = f"[{level}] Line {line}: {message_nepali}\n"
    formatted += f"[ENGLISH] Line {line}: {message_english}\n"
    if source:
        formatted += f"          {source}\n"
        formatted += f"          {'^' * len(source)}\n"
    if suggestion:
        formatted += f"          {suggestion}\n"
    return formatted


# Error catalog
ERROR_MESSAGES = {
    'E001': {  # Unterminated string
        'nepali': "अपूर्ण स्ट्रिङ (Incomplete string)। \" को जोडी छुट्यो।",
        'english': "Unterminated string. Missing closing quote.",
        'suggestion': "Tip: दुवै छेउमा \" राख्नुहोस् / Tip: Add quotes on both sides."
    },
    'E002': {  # Missing bhane after yedi
        'nepali': "'yedi' (if) लाई 'bhane' (then) चाहिन्छ।",
        'english': "'yedi' (if) requires 'bhane' (then).",
        'suggestion': "Did you mean: yedi x > 5 bhane"
    },
    'E003': {  # Undeclared variable
        'nepali': "'{var}' परिभाषित भएको छैन (not defined)।",
        'english': "'{var}' is not defined.",
        'suggestion': "Tip: पहिले 'rakha {var} = ...' गर्नुहोस् / Tip: First declare with 'rakha {var} = ...'"
    },
    'E004': {  # Missing antya (end block)
        'nepali': "'{keyword}' को 'antya' (end) छुट्यो।",
        'english': "Missing 'antya' (end) for '{keyword}'.",
        'suggestion': "Tip: हरेक '{keyword}' लाई 'antya' ले बन्द गर्नुहोस् / Tip: Every '{keyword}' must be closed with 'antya'."
    },
    'E005': {  # Invalid character
        'nepali': "अमान्य अक्षर (Invalid character) '{char}'।",
        'english': "Invalid character '{char}'.",
        'suggestion': "Tip: संख्या 0-9 मात्र प्रयोग गर्नुहोस् / Tip: Use only digits 0-9."
    },
    'E006': {  # Division by zero
        'nepali': "शून्यले भाग गर्न मिल्दैन (Cannot divide by zero)।",
        'english': "Division by zero.",
        'suggestion': "Tip: भाग गर्ने संख्या 0 हुनु हुँदैन / Tip: The divisor cannot be zero."
    }
}


if __name__ == '__main__':
    print("Error reporter module loaded")