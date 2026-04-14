# Paper Draft

This directory contains an anonymous ICML-style draft aligned with the current
SIAS codebase.

## Template Source

- Style follows ICML 2025 author instructions.
- Local files:
  - `icml2025.sty`
  - `icml2025.bst`
  - `math_commands.tex`

These files were pulled from a public ICML 2025 LaTeX template repository that
tracks the conference formatting package.

## Files

- `main.tex`: anonymous paper draft
- `references.bib`: bibliography

## Build

```bash
cd paper
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

If `latexmk` is available:

```bash
cd paper
latexmk -pdf main.tex
```
