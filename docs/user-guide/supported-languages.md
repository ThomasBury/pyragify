# Supported Languages

Pyragify supports multiple programming languages with varying levels of analysis depth. This guide details the parsing capabilities for each supported language.

## Language Support Overview

| Language | Parser | Status | Features |
|----------|--------|--------|----------|
| Python | AST | ✅ Full | Functions, classes, imports, calls, inheritance |
| JavaScript | Tree-sitter → Regex | ⚠️ Partial* | Functions, classes, imports (automatic fallback) |
| TypeScript | Tree-sitter → Regex | ⚠️ Partial* | Functions, classes, imports (automatic fallback) |
| Java | Tree-sitter → Regex | ⚠️ Partial* | Methods, classes, imports (automatic fallback) |
| C | Tree-sitter → Regex | ⚠️ Partial* | Functions, structs, includes (automatic fallback) |
| C++ | Tree-sitter → Regex | ⚠️ Partial* | Functions, classes, includes (automatic fallback) |
| Markdown | Regex | ✅ Full | Headers, sections, content |
| HTML | Regex | ✅ Full | Scripts, styles, structure |
| CSS | Regex | ✅ Full | Rules, selectors |
| Other | Basic | ✅ Basic | File content as single chunk |

\* *Status depends on tree-sitter package compatibility. Automatic fallback to regex parsing ensures reliability.*

## Python (Full Support)

### Parsing Method
- **AST (Abstract Syntax Tree)**: Precise, language-aware parsing
- **Fallback**: None needed - AST parsing is robust

### Supported Constructs

#### Functions
```python
def calculate_total(items, tax_rate=0.1):
    """Calculate total with tax."""
    subtotal = sum(item.price for item in items)
    return subtotal * (1 + tax_rate)
```

**Extracted Information:**
- Function name: `calculate_total`
- Parameters: `items`, `tax_rate`
- Docstring: `"Calculate total with tax."`
- Return type: Inferred from usage
- Line numbers: Start and end positions

#### Classes
```python
class ShoppingCart:
    """A shopping cart with items."""

    def __init__(self):
        self.items = []

    def add_item(self, item):
        """Add item to cart."""
        self.items.append(item)

    def get_total(self):
        """Calculate total price."""
        return calculate_total(self.items)
```

**Extracted Information:**
- Class name: `ShoppingCart`
- Methods: `add_item`, `get_total`
- Inheritance: Parent classes
- Docstrings: Class and method documentation

#### Imports
```python
import os
import sys
from pathlib import Path
from typing import List, Optional
```

**Extracted Information:**
- Module names: `os`, `sys`, `pathlib`, `typing`
- Import types: Direct vs. from imports
- Aliases: `Path`, `List`, `Optional`

#### Function Calls
```python
# Direct calls
result = calculate_total(items)

# Method calls
cart.add_item(item)

# Attribute access
obj.method().another_method()
```

**Extracted Information:**
- Caller and callee relationships
- Line numbers for call sites
- Context information

### Knowledge Graph Integration

Python entities are fully integrated into the knowledge graph:

- **Nodes**: Functions, classes, modules, files
- **Edges**: `imports`, `calls`, `inherits`, `contains`
- **Metadata**: Docstrings, parameters, line numbers

## JavaScript/TypeScript (Partial Support)

### Parsing Method
- **Primary**: Tree-sitter (when available)
- **Fallback**: Regex-based parsing
- **Status**: ⚠️ Version compatibility issues may cause fallback

### Supported Constructs

#### Functions
```javascript
// Function declaration
function calculateTotal(items, taxRate = 0.1) {
    const subtotal = items.reduce((sum, item) => sum + item.price, 0);
    return subtotal * (1 + taxRate);
}

// Arrow function
const calculateTotal = (items, taxRate = 0.1) => {
    const subtotal = items.reduce((sum, item) => sum + item.price, 0);
    return subtotal * (1 + taxRate);
};
```

#### Classes
```javascript
class ShoppingCart {
    constructor() {
        this.items = [];
    }

    addItem(item) {
        this.items.push(item);
    }

    getTotal() {
        return calculateTotal(this.items);
    }
}
```

#### Imports/Exports
```javascript
// ES6 imports
import { calculateTotal } from './utils';
import ShoppingCart from './cart';

// CommonJS
const utils = require('./utils');
```

### Tree-sitter vs Regex Fallback

Pyragify uses an intelligent fallback system to ensure reliable parsing across different environments.

#### Tree-sitter (Preferred When Available)
- **Accurate AST parsing**: Precise syntax tree analysis
- **Full context awareness**: Understands complex language constructs
- **Better relationship extraction**: Captures nuanced dependencies and references
- **Advanced features**: Supports modern language features and patterns

#### Automatic Regex Fallback
When tree-sitter is unavailable or fails, Pyragify automatically falls back to regex-based parsing:

- **Basic pattern matching**: Reliable detection of common constructs
- **Language-specific patterns**: Tailored regex for each supported language
- **Essential features preserved**: Core functionality remains intact
- **Performance**: Fast processing with minimal dependencies

#### Fallback Triggers
The system automatically switches to regex parsing when:
- Tree-sitter packages are not installed
- Version compatibility issues occur
- Parsing fails for specific files
- Memory or performance constraints are detected

!!! info "Fallback Transparency"
    Users typically won't notice the fallback - Pyragify handles this automatically and logs the change for transparency.

## Java (Partial Support)

### Parsing Method
- **Primary**: Tree-sitter
- **Fallback**: Regex-based parsing

### Supported Constructs

#### Classes and Methods
```java
public class ShoppingCart {
    private List<Item> items;

    public ShoppingCart() {
        this.items = new ArrayList<>();
    }

    public void addItem(Item item) {
        this.items.add(item);
    }

    public double getTotal() {
        return calculateTotal(this.items);
    }
}
```

#### Inheritance
```java
public class PremiumCart extends ShoppingCart {
    private double discountRate;

    @Override
    public double getTotal() {
        return super.getTotal() * (1 - discountRate);
    }
}
```

#### Imports
```java
import java.util.List;
import java.util.ArrayList;
import com.example.Item;
```

## C/C++ (Partial Support)

### Parsing Method
- **Primary**: Tree-sitter
- **Fallback**: Regex-based parsing

### Supported Constructs

#### Functions
```cpp
double calculate_total(const std::vector<Item>& items, double tax_rate = 0.1) {
    double subtotal = 0.0;
    for (const auto& item : items) {
        subtotal += item.price;
    }
    return subtotal * (1 + tax_rate);
}
```

#### Classes/Structs
```cpp
class ShoppingCart {
private:
    std::vector<Item> items;

public:
    ShoppingCart() : items() {}

    void addItem(const Item& item) {
        items.push_back(item);
    }

    double getTotal() const {
        return calculate_total(items);
    }
};
```

#### Includes
```cpp
#include <vector>
#include <iostream>
#include "item.h"
#include "cart.h"
```

## Markdown (Full Support)

### Parsing Method
- **Header-based chunking**: Splits content by header levels
- **Content preservation**: Maintains formatting and structure

### Supported Constructs

```markdown
# Main Title

This is content under the main title.

## Subsection

Content under subsection.

### Sub-subsection

More detailed content.

## Another Section

Different section content.
```

**Extracted Chunks:**
- Header level and text
- Associated content
- Hierarchical relationships

## HTML (Full Support)

### Parsing Method
- **Tag-based extraction**: Identifies scripts, styles, and structure
- **Content isolation**: Separates different content types

### Supported Constructs

```html
<!DOCTYPE html>
<html>
<head>
    <title>Shopping Cart</title>
    <style>
        .cart { border: 1px solid #ccc; }
    </style>
</head>
<body>
    <script>
        function calculateTotal(items) {
            return items.reduce((sum, item) => sum + item.price, 0);
        }
    </script>

    <div class="cart">
        <!-- Cart content -->
    </div>
</body>
</html>
```

**Extracted Elements:**
- Script blocks
- Style blocks
- Structural content

## CSS (Full Support)

### Parsing Method
- **Rule-based parsing**: Extracts CSS rules and selectors
- **Property preservation**: Maintains formatting

### Supported Constructs

```css
/* Basic styles */
.cart {
    border: 1px solid #ccc;
    padding: 10px;
}

/* Responsive design */
@media screen and (max-width: 768px) {
    .cart {
        padding: 5px;
    }
}

/* Animations */
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}
```

## Other Languages (Basic Support)

### Parsing Method
- **File content**: Entire file as single chunk
- **Basic metadata**: File size, type, name

### Supported Files
- Plain text files
- Configuration files
- Documentation files
- Any text-based format

## Language Detection

Pyragify automatically detects languages based on:

1. **File extensions**:
   - `.py` → Python
   - `.js` → JavaScript
   - `.ts` → TypeScript
   - `.java` → Java
   - `.c` → C
   - `.cpp` → C++
   - `.md` → Markdown
   - `.html` → HTML
   - `.css` → CSS

2. **Content analysis**: Fallback detection for files without standard extensions

3. **Shebang lines**: For script files with `#!/usr/bin/env python`

## Configuration by Language

You can customize processing per language:

```yaml
# Language-specific settings (future feature)
languages:
  python:
    extract_docstrings: true
    extract_types: true
  javascript:
    extract_comments: true
    extract_types: false
```

## Performance Considerations

### Parsing Speed

| Language | Parser | Relative Speed |
|----------|--------|----------------|
| Python | AST | Very Fast ⚡ |
| Markdown | Regex | Fast ⚡ |
| HTML/CSS | Regex | Fast ⚡ |
| JavaScript | Tree-sitter | Medium ⚠️ |
| Java | Tree-sitter | Medium ⚠️ |
| C/C++ | Tree-sitter | Medium ⚠️ |

### Memory Usage

- **Python**: Low - AST is memory efficient
- **Tree-sitter languages**: Medium - Tree-sitter builds syntax trees
- **Regex languages**: Low - Simple pattern matching

### Recommendations

#### For Large Codebases
```yaml
# Focus on high-value languages
skip_patterns:
  - "*.min.js"    # Skip minified files
  - "*.min.css"   # Skip minified styles

# Optimize for performance
max_file_size: 52428800  # 50 MB limit
```

#### For Analysis Depth
```yaml
# Enable graph for supported languages
graph:
  enabled: true
  relationships:
    - "imports"
    - "calls"
    - "inherits"
```

## Troubleshooting Language Issues

### Python Parsing Errors

**Issue:** Syntax errors in Python files
```python
# This will cause AST parsing to fail
def broken_function(
    return "incomplete"
```

**Solution:**
- Fix syntax errors in source files
- Pyragify will skip malformed files with warnings

### Tree-sitter Fallbacks

**Issue:** Tree-sitter parsing fails
```
WARNING: Tree-sitter parsing failed for javascript: version compatibility
```

**Solution:**
- This is normal - regex fallback will be used
- Check that tree-sitter packages are installed
- Some advanced features may not be available

### Encoding Issues

**Issue:** Files with unusual encodings
```
ERROR: 'utf-8' codec can't decode byte 0x89
```

**Solution:**
- Ensure files are UTF-8 encoded
- Pyragify skips binary files automatically
- Check file encoding: `file filename`

### Large File Handling

**Issue:** Very large files cause performance issues
```
WARNING: Skipping large file: size exceeds limit
```

**Solution:**
- Increase `max_file_size` in configuration
- Consider splitting large files
- Use `skip_patterns` to exclude problematic files

## Contributing Language Support

### Adding New Languages

To add support for a new language:

1. **Choose parser type**:
   - AST (if language has Python-like AST support)
   - Tree-sitter (if grammar exists)
   - Regex (for simple languages)

2. **Implement parser**:
   ```python
   def parse_new_language(file_path: Path) -> List[Dict]:
       # Your parsing logic here
       pass
   ```

3. **Add to FILE_TYPE_MAP**:
   ```python
   FILE_TYPE_MAP = {
       ".newlang": "new_language",
       # ... existing mappings
   }
   ```

4. **Update chunk_file method**:
   ```python
   elif suffix == ".newlang":
       chunks, line_count = self.parse_new_language(file_path)
   ```

### Improving Existing Parsers

- **Fix tree-sitter compatibility issues**
- **Add more construct types**
- **Improve accuracy of relationship extraction**
- **Add language-specific metadata**

## Future Language Support

### Planned Additions

- **Go**: Tree-sitter based parsing
- **Rust**: Tree-sitter based parsing
- **Ruby**: AST-based parsing
- **PHP**: Tree-sitter based parsing
- **Swift**: Tree-sitter based parsing

### Enhanced Features

- **Type information extraction**
- **Comment and documentation parsing**
- **Dependency graph analysis**
- **Cross-language reference resolution**

The language support in Pyragify continues to evolve. Python has the most mature support, while other languages benefit from tree-sitter's advanced parsing capabilities with regex fallbacks for reliability.