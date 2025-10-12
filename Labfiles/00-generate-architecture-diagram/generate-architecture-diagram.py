"""
Generate Architecture Diagrams from Source Code using LLM
==========================================================

This script demonstrates how to use an LLM to analyze a codebase
and generate Mermaid flow diagrams similar to the Azure AI Agent architecture.

Usage:
    python generate-architecture-diagram.py
"""

import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

# Configuration
ENDPOINT = os.getenv("AZURE_OPENAI_MODEL_ENDPOINT")
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
MODEL = os.getenv("AZURE_OPENAI_MODEL_DEPLOYMENT_NAME")
API_VERSION = "2024-08-01-preview"


def scan_repository_structure(root_path: Path, max_depth: int = 3) -> str:
    """Scan repository structure and return a formatted string."""
    structure = []
    
    def scan_dir(path: Path, depth: int = 0, prefix: str = ""):
        if depth > max_depth:
            return
        
        try:
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
            for i, item in enumerate(items):
                is_last = i == len(items) - 1
                connector = "└── " if is_last else "├── "
                
                # Skip common ignore patterns
                if item.name in ['.git', '__pycache__', 'node_modules', '.venv', 'venv']:
                    continue
                
                structure.append(f"{prefix}{connector}{item.name}")
                
                if item.is_dir():
                    extension = "    " if is_last else "│   "
                    scan_dir(item, depth + 1, prefix + extension)
        except PermissionError:
            pass
    
    scan_dir(root_path)
    return "\n".join(structure)


def extract_key_files(root_path: Path, extensions: list[str] = ['.py', '.js', '.ts']) -> dict[str, str]:
    """Extract content from key files in the repository."""
    key_files = {}
    
    for ext in extensions:
        for file in root_path.rglob(f"*{ext}"):
            # Skip certain directories
            if any(part in file.parts for part in ['node_modules', '__pycache__', '.venv', 'venv', '.git']):
                continue
            
            # Limit to main files (entry points, etc.)
            if any(keyword in file.name for keyword in ['main', 'app', 'index', 'agent', 'client', 'server']):
                try:
                    relative_path = file.relative_to(root_path)
                    content = file.read_text(encoding='utf-8')
                    
                    # Truncate very large files
                    if len(content) > 10000:
                        lines = content.split('\n')
                        content = '\n'.join(lines[:200]) + f"\n... (truncated, {len(lines)} total lines)"
                    
                    key_files[str(relative_path)] = content
                except Exception as e:
                    print(f"Could not read {file}: {e}")
    
    return key_files


def build_analysis_prompt(repo_structure: str, key_files: dict[str, str]) -> str:
    """Build a comprehensive prompt for LLM analysis."""
    
    prompt = """# Task: Generate Architecture Flow Diagram

Analyze the provided repository structure and code samples, then generate a comprehensive Mermaid flow diagram.

## Requirements:

1. **Flow Type**: Use Mermaid flowchart (graph TD or graph LR)
2. **Component Grouping**: Use subgraphs to group related components
3. **Data Flow**: Show directional arrows indicating data/control flow
4. **External Services**: Highlight integrations with external APIs/services
5. **Key Interactions**: Show important interactions between components
6. **Clear Labels**: Use descriptive labels for nodes and edges
7. **Professional Style**: Follow the style from Azure documentation

## Output Format:

```mermaid
graph TD
    subgraph "Component Group"
        A[Component A] --> B[Component B]
    end
    
    B --> C[External Service]
    
    style A fill:#e1f5ff
    style C fill:#ffe1e1
```

## Repository Structure:

```
"""
    
    prompt += repo_structure + "\n```\n\n"
    
    prompt += "## Key Files Analysis:\n\n"
    
    for file_path, content in key_files.items():
        prompt += f"### {file_path}\n\n```\n{content}\n```\n\n"
    
    prompt += """
## Analysis Focus:

1. Identify the main entry point(s)
2. Map out the primary data/control flow
3. Identify external dependencies (APIs, databases, services)
4. Recognize architectural patterns (client-server, MVC, etc.)
5. Group related components logically
6. Highlight important interactions

## Generate:

1. A high-level architecture overview diagram
2. Detailed component interaction flow
3. Color-coded by component type (user code, frameworks, services)

Please provide the Mermaid diagram with detailed annotations.
"""
    
    return prompt


def generate_diagram_with_llm(prompt: str) -> str:
    """Call the LLM to generate the diagram."""
    
    client = AzureOpenAI(
        azure_endpoint=ENDPOINT,
        api_key=API_KEY,
        api_version=API_VERSION
    )
    
    messages = [
        {"role": "system", "content": """You are an expert software architect specializing in 
creating clear, comprehensive architecture diagrams. You excel at analyzing code 
and producing professional Mermaid diagrams that clearly show system architecture, 
data flow, and component interactions."""},
        {"role": "user", "content": prompt}
    ]
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.3,  # Lower temperature for more consistent output
        max_tokens=4000
    )
    
    return response.choices[0].message.content


async def main():
    """Main execution flow."""
    
    print("=== Repository Architecture Diagram Generator ===\n")
    
    # Get the current workspace
    current_dir = Path(__file__).parent
    print(f"Analyzing repository: {current_dir}\n")
    
    # Step 1: Scan repository structure
    print("1. Scanning repository structure...")
    repo_structure = scan_repository_structure(current_dir, max_depth=2)
    print(f"   Found {len(repo_structure.split(chr(10)))} items\n")
    
    # Step 2: Extract key files
    print("2. Extracting key file contents...")
    key_files = extract_key_files(current_dir)
    print(f"   Extracted {len(key_files)} key files\n")
    
    for file_path in key_files.keys():
        print(f"   - {file_path}")
    
    # Step 3: Build analysis prompt
    print("\n3. Building analysis prompt...")
    prompt = build_analysis_prompt(repo_structure, key_files)
    print(f"   Prompt size: {len(prompt)} characters\n")
    
    # Step 4: Generate diagram with LLM
    print("4. Generating diagram with LLM...")
    print("   (This may take 30-60 seconds...)\n")
    
    diagram = generate_diagram_with_llm(prompt)
    
    # Step 5: Save results
    output_file = current_dir / "generated-architecture-diagram.md"
    
    with output_file.open('w', encoding='utf-8') as f:
        f.write("# Generated Architecture Diagram\n\n")
        f.write("## Mermaid Diagram\n\n")
        f.write(diagram)
        f.write("\n\n---\n\n")
        f.write("## Repository Structure\n\n```\n")
        f.write(repo_structure)
        f.write("\n```\n")
    
    print(f"✓ Diagram generated and saved to: {output_file}\n")
    print("=" * 50)
    print("\nPreview:\n")
    print(diagram[:500] + "...\n")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
