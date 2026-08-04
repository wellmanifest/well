# well


## AI Cost Tracking

![PyPI](https://img.shields.io/badge/pypi-costs-blue) ![Version](https://img.shields.io/badge/version-0.1.4-blue) ![Python](https://img.shields.io/badge/python-3.9+-blue) ![License](https://img.shields.io/badge/license-Apache--2.0-green)
![AI Cost](https://img.shields.io/badge/AI%20Cost-$0.01-orange) ![Human Time](https://img.shields.io/badge/Human%20Time-1.2h-blue) ![Model](https://img.shields.io/badge/Model-openrouter%2Fqwen%2Fqwen3--coder--next-lightgrey)

- 🤖 **LLM usage:** $0.0103 (6 commits)
- 👤 **Human dev:** ~$118 (1.2h @ $100/h, 30min dedup)

Generated on 2026-08-04 using [openrouter/qwen/qwen3-coder-next](https://openrouter.ai/qwen/qwen3-coder-next)

---

Minimalny pakiet Pythona o nazwie `well`.

```bash
from well import hello, greet

hello()          # -> "hello from well"
greet("Anna")    # -> "Hello, Anna!"
```

Instalacja:

```bash
pip install wellm
```

## API

- `hello() -> str`  
  Zwraca podstawowy string powitalny.

- `greet(name: str = "world") -> str`  
  Zwraca spersonalizowane powitanie `Hello, {name}!`.

## Przykłady

```python
from well import hello, greet

print(hello())
print(greet())
print(greet("Piotr"))
```



## License

Licensed under Apache-2.0.
