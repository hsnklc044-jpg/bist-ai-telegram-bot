"""
QuantBIST
The /tara expression language: a small tokenizer and a recursive-descent parser written for it.
Nothing the user types is ever executed; it only becomes a tree of known nodes.

    rsi<35 · ema20>ema50 · rsi 30..50 · rsi(7)>70 · sma200<kapanis
    kesti_yukari(ema20,ema50) · kesti_asagi(macd,macd_sinyal) · son(5, kesti_yukari(...))
    ve / veya / değil and parentheses; conditions side by side mean "ve"
    options: evren=bist100|bist30|izleme · likidite=10 (million TL, 0 = off) ·
             sirala=alfabetik|goreli_guc|hacim|rsi · rejim=yukselis|dusus|karisik|yuksek_oynaklik

At most 400 characters and 15 conditions. Errors name the place (a caret under the normalized
text) and the nearest valid field.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from core.screen import fields as F

MAX_LENGTH = 400
MA_PERIODS = (5, 10, 20, 40, 50, 100, 150, 200)  # the periods the user's screens use (görev 28.10, Aşama A)
MAX_CONDITIONS = 15  # the user's own "Düşeni Kıran" screen has 14 price conditions (DECISIONS K-34)
PARAM_RANGE = (2, 250)
WINDOW_RANGE = (1, 60)
EXAMPLE = "Örnek: /tara rsi<30 ema20>ema50"
UNIVERSES = ("bist100", "bist30", "izleme", "quantbist")
ORDERS = ("alfabetik", "goreli_guc", "hacim", "rsi")
# rejim= (Talimat C, K-51): a filter on the market regime label, never a signal
REGIMES = {"yukselis": "yükseliş", "dusus": "düşüş", "karisik": "karışık", "yuksek_oynaklik": "yüksek oynaklık"}
DEFAULT_LIQUIDITY = 15.0  # million TL, previous 20 sessions (core.screen.elimination, K-45)
_ASCII = str.maketrans("ığüşöç", "igusoc")
_ALLOWED = set("abcdefghijklmnopqrstuvwxyz0123456789_(),<>=:.- ")
KEYWORDS = {"ve", "veya", "degil", "and", "or", "not"}


class ScreenError(ValueError):
    def __init__(self, message: str, text: str = "", column: int | None = None):
        caret = f"\n{text}\n{' ' * column}^" if column is not None else ""
        super().__init__(f"⚠️ {message}{caret}\n{EXAMPLE}")


def normalize(text: str) -> str:
    text = text.replace("İ", "i").replace("I", "ı").lower().translate(_ASCII)
    return " ".join(text.split())


# --- tokens ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Token:
    kind: str  # name, number, op, range, lparen, rparen, comma, assign, end
    value: object
    pos: int


def tokenize(text: str) -> list[Token]:
    tokens, i = [], 0
    while i < len(text):
        ch = text[i]
        if ch == " ":
            i += 1
        elif ch not in _ALLOWED:
            raise ScreenError(f"İfadede izin verilmeyen karakter '{ch}'.", text, i)
        elif ch.isdigit() or (ch == "-" and i + 1 < len(text) and text[i + 1].isdigit()):
            j = i + 1
            while j < len(text) and text[j].isdigit():
                j += 1
            if j + 1 < len(text) and text[j] in ".," and text[j + 1].isdigit() and text[j:j + 2] != "..":
                j += 1
                while j < len(text) and text[j].isdigit():
                    j += 1
            tokens.append(Token("number", float(text[i:j].replace(",", ".")), i))
            i = j
        elif ch.isalpha() or ch == "_":
            j = i
            while j < len(text) and (text[j].isalnum() or text[j] == "_"):
                j += 1
            tokens.append(Token("name", text[i:j], i))
            i = j
        elif text.startswith("..", i):
            tokens.append(Token("range", "..", i))
            i += 2
        elif ch in "<>":
            op = text[i:i + 2] if text[i + 1:i + 2] == "=" else ch
            tokens.append(Token("op", op, i))
            i += len(op)
        elif ch in "=:":
            tokens.append(Token("assign", ch, i))
            i += 1
        elif ch in "(),":
            tokens.append(Token({"(": "lparen", ")": "rparen", ",": "comma"}[ch], ch, i))
            i += 1
        else:  # a lone "." or "-"
            raise ScreenError(f"Burada '{ch}' beklenmiyordu.", text, i)
    tokens.append(Token("end", None, len(text)))
    return tokens


# --- tree -----------------------------------------------------------------------------------------


def _number(x: float) -> str:
    return f"{x:g}"


# Three-valued logic on numpy arrays: each node gives (value, known). A missing input is unknown,
# and only a known True ever matches; "değil" of unknown stays unknown (Kleene logic).


@dataclass(frozen=True)
class Operand:
    key: str | None  # field key, or None for a number
    value: float | None = None

    @property
    def text(self) -> str:
        return self.key if self.key is not None else _number(self.value)

    def array(self, t: pd.DataFrame) -> np.ndarray:
        if self.key is None:
            return np.full(len(t), self.value, dtype=float)
        return t[self.key].to_numpy(dtype=float)


class Node:
    leaf = False

    def truth(self, t: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        raise NotImplementedError

    def mask(self, t: pd.DataFrame) -> pd.Series:
        value, known = self.truth(t)
        return pd.Series(value & known, index=t.index)

    def leaves(self) -> list[Node]:
        return [self]


_OPS = {"<": np.less, ">": np.greater, "<=": np.less_equal, ">=": np.greater_equal}


def _compare(left: np.ndarray, op: str, right: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    known = ~(np.isnan(left) | np.isnan(right))
    with np.errstate(invalid="ignore"):
        value = _OPS[op](left, right) & known
    return value, known


def _shift(a: np.ndarray) -> np.ndarray:
    out = np.empty_like(a)
    out[0] = np.nan
    out[1:] = a[:-1]
    return out


@dataclass(frozen=True)
class Compare(Node):
    left: Operand
    op: str
    right: Operand
    leaf = True

    def text(self, nested: bool = False) -> str:
        return f"{self.left.text}{self.op}{self.right.text}"

    def truth(self, t):
        return _compare(self.left.array(t), self.op, self.right.array(t))


@dataclass(frozen=True)
class LevelBreak(Compare):
    """kirdi_yukari(direnc) / kirdi_asagi(destek): the 1/0 level-break field equals 1 (K-49)."""

    def text(self, nested: bool = False) -> str:
        return "kirdi_yukari(direnc)" if self.left.key == "kirdi_yukari" else "kirdi_asagi(destek)"


@dataclass(frozen=True)
class Range(Node):
    operand: Operand
    low: float
    high: float
    leaf = True

    def text(self, nested: bool = False) -> str:
        return f"{self.operand.text} {_number(self.low)}..{_number(self.high)}"

    def truth(self, t):
        x = self.operand.array(t)
        known = ~np.isnan(x)
        with np.errstate(invalid="ignore"):
            return (x >= self.low) & (x <= self.high) & known, known


@dataclass(frozen=True)
class Cross(Node):
    up: bool
    a: Operand
    b: Operand
    leaf = True

    def text(self, nested: bool = False) -> str:
        return f"kesti_{'yukari' if self.up else 'asagi'}({self.a.text},{self.b.text})"

    def truth(self, t):
        a, b = self.a.array(t), self.b.array(t)
        pa, pb = _shift(a), _shift(b)
        known = ~(np.isnan(a) | np.isnan(b) | np.isnan(pa) | np.isnan(pb))
        with np.errstate(invalid="ignore"):
            now = (a > b) if self.up else (a < b)
            before = (pa <= pb) if self.up else (pa >= pb)
        return now & before & known, np.ones(len(a), dtype=bool)


@dataclass(frozen=True)
class Within(Node):
    days: int
    child: Node

    def text(self, nested: bool = False) -> str:
        return f"son({self.days},{self.child.text(False)})"

    def truth(self, t):
        value, known = self.child.truth(t)
        hits = np.cumsum((value & known).astype(int))
        before = np.concatenate([np.zeros(self.days, dtype=int), hits[:-self.days]]) if len(hits) > self.days \
            else np.zeros(len(hits), dtype=int)
        return (hits - before) > 0, np.ones(len(hits), dtype=bool)

    def leaves(self):
        return [self]


@dataclass(frozen=True)
class Not(Node):
    child: Node

    def text(self, nested: bool = False) -> str:
        return f"degil {self.child.text(True)}"

    def truth(self, t):
        value, known = self.child.truth(t)
        return known & ~value, known

    def leaves(self):
        return self.child.leaves()


@dataclass(frozen=True)
class And(Node):
    children: tuple

    def text(self, nested: bool = False) -> str:
        s = " ve ".join(c.text(True) for c in self.children)
        return f"({s})" if nested else s

    def truth(self, t):
        value, known = self.children[0].truth(t)
        for c in self.children[1:]:
            v, k = c.truth(t)
            value, known = value & v, (known & k) | (known & ~value) | (k & ~v)
        return value & known, known

    def leaves(self):
        return [leaf for c in self.children for leaf in c.leaves()]


@dataclass(frozen=True)
class Or(Node):
    children: tuple

    def text(self, nested: bool = False) -> str:
        return "(" + " veya ".join(c.text(True) for c in self.children) + ")"

    def truth(self, t):
        value, known = self.children[0].truth(t)
        for c in self.children[1:]:
            v, k = c.truth(t)
            value, known = value | v, (known & k) | value | v
        return value, known

    def leaves(self):
        return [leaf for c in self.children for leaf in c.leaves()]


@dataclass
class Query:
    root: Node
    universe: str = "bist100"
    elimination: object = None  # core.screen.elimination.Settings (filled in __post_init__)
    order: str = "alfabetik"
    fields: set = field(default_factory=set)
    template: str = ""  # the ready-made template it came from (core.screen.templates)
    regime: str = ""  # rejim= option: a key of REGIMES, or "" for every regime

    def __post_init__(self):
        if self.elimination is None:
            from core.screen.elimination import Settings

            self.elimination = Settings()

    @property
    def liquidity(self) -> float:
        return self.elimination.liquidity

    @property
    def text(self) -> str:
        """The criterion: the expression plus non-default universe and eliminations (the order is not part of it)."""

        options = []
        if self.universe != "bist100":
            options.append(f"evren={self.universe}")
        if self.regime:
            options.append(f"rejim={self.regime}")
        return " ".join([self.root.text(False), *options, *self.elimination.options()])

    def truth(self, t: pd.DataFrame):
        return self.root.truth(t)

    def mask(self, t: pd.DataFrame) -> pd.Series:
        return self.root.mask(t)

    def leaves(self) -> list[Node]:
        return self.root.leaves()


# --- parser ---------------------------------------------------------------------------------------


class _Parser:
    def __init__(self, text: str):
        self.text = text
        self.tokens = tokenize(text)
        self.i = 0
        self.fields: set[str] = set()
        self.options: dict[str, object] = {}
        self.conditions = 0

    @property
    def tok(self) -> Token:
        return self.tokens[self.i]

    def error(self, message: str, pos: int | None = None):
        raise ScreenError(message, self.text, self.tok.pos if pos is None else pos)

    def take(self, kind: str, message: str) -> Token:
        if self.tok.kind != kind:
            self.error(message)
        token = self.tok
        self.i += 1
        return token

    def is_word(self, *words: str) -> bool:
        return self.tok.kind == "name" and self.tok.value in words

    # query := item* ; item := option | expression part (side by side = ve)
    def query(self) -> Query:
        root = self.or_expr(top=True)
        if self.tok.kind == "rparen":
            self.error("Burada fazladan ')' var.")
        if self.tok.kind != "end":
            self.error("Burada bir koşul ya da 've'/'veya' bekleniyordu.")
        if root is None:
            self.error("En az bir koşul yazın.", 0)
        from core.screen.elimination import Settings

        settings = Settings()
        if self.options.get("ele") is False:
            settings = Settings.off()
        for name in ("likidite", "ele_likidite", "ele_kurumsal", "ele_hareket", "ele_veri"):
            if name in self.options:
                settings = settings.with_option(name, self.options[name])
        return Query(root, self.options.get("evren", "bist100"), settings, self.options.get("sirala", "alfabetik"),
                     self.fields, regime=self.options.get("rejim", ""))

    def starts_term(self) -> bool:
        t = self.tok
        return t.kind in ("lparen", "number") or (t.kind == "name" and t.value not in ("ve", "veya", "and", "or"))

    def or_expr(self, top: bool = False) -> Node | None:
        parts = [self.and_expr(top)]
        while self.is_word("veya", "or"):
            self.i += 1
            parts.append(self.and_expr(top))
        parts = [p for p in parts if p is not None]
        if not parts:
            return None
        return parts[0] if len(parts) == 1 else Or(tuple(parts))

    def and_expr(self, top: bool) -> Node | None:
        parts = []
        while True:
            if top and self.option():
                continue
            if self.is_word("ve", "and") or (self.tok.kind == "comma" and top):
                self.i += 1
                continue
            if not self.starts_term():
                break
            parts.append(self.not_expr())
        if not parts:
            if not top:
                self.error("Burada bir koşul bekleniyordu.")
            return None
        return parts[0] if len(parts) == 1 else And(tuple(parts))

    def not_expr(self) -> Node:
        if self.is_word("degil", "not"):
            self.i += 1
            return Not(self.not_expr())
        return self.primary()

    def primary(self) -> Node:
        if self.tok.kind == "lparen":
            opened = self.tok.pos
            self.i += 1
            node = self.or_expr()
            if self.tok.kind != "rparen":
                self.error(f"Burada kapanmamış parantez var (açıldığı yer: {opened + 1}. karakter).")
            self.i += 1
            return node
        if self.is_word("kesti_yukari", "kesti_asagi"):
            up = self.tok.value == "kesti_yukari"
            self.i += 1
            self.take("lparen", "Kesişim için parantez açın: kesti_yukari(ema20,ema50).")
            a = self.operand()
            self.take("comma", "Kesişim iki değer ister: kesti_yukari(ema20,ema50).")
            b = self.operand()
            self.take("rparen", "Kesişimi ')' ile kapatın.")
            return self.count(Cross(up, a, b))
        if self.is_word("kirdi_yukari", "kirdi_asagi"):
            name = self.tok.value
            target = "direnc" if name == "kirdi_yukari" else "destek"
            usage = f"{name}({target}) yazın."
            self.i += 1
            self.take("lparen", usage)
            word = self.take("name", usage)
            if word.value != target:
                self.error(f"{name} yalnız {target} ile yazılır: {usage}", word.pos)
            self.take("rparen", usage)
            self.fields.add(name)
            return self.count(LevelBreak(Operand(name), ">=", Operand(None, 1.0)))
        if self.is_word("son"):
            self.i += 1
            self.take("lparen", "Pencere için: son(5, kesti_yukari(ema20,ema50)).")
            days = self.take("number", "son(...) önce gün sayısı ister: son(5, ...).")
            if days.value != int(days.value) or not WINDOW_RANGE[0] <= days.value <= WINDOW_RANGE[1]:
                self.error(f"Gün sayısı {WINDOW_RANGE[0]} ile {WINDOW_RANGE[1]} arasında bir tam sayı olmalı.",
                           days.pos)
            self.take("comma", "son(gün, koşul): araya virgül.")
            child = self.or_expr()
            if child is None:
                self.error("son(...) içinde bir koşul bekleniyordu.")
            self.take("rparen", "son(...)'u ')' ile kapatın.")
            return Within(int(days.value), child)
        start = self.tok.pos
        left = self.operand()
        if self.tok.kind == "number" and self.tokens[self.i + 1].kind == "range":
            low = self.take("number", "").value
            self.i += 1
            high = self.take("number", "Aralığın üst sınırı eksik: rsi 30..50.").value
            if low > high:
                self.error("Aralıkta küçük sayı önce yazılır: rsi 30..50.", start + len(left.text) + 1)
            if left.key is None:
                self.error("Aralıkta solda bir alan olmalı: rsi 30..50.", start)
            return self.count(Range(left, low, high))
        if self.tok.kind == "assign":
            self.error("Karşılaştırma için < ya da > kullanın (= desteklenmiyor).")
        if self.tok.kind != "op":
            self.error("Burada < ya da > bekleniyordu (ör. rsi<30).")
        op = self.tok.value
        self.i += 1
        if self.tok.kind not in ("name", "number"):
            self.error("Karşılaştırmanın sağ tarafı eksik.")
        right = self.operand()
        if left.key is None and right.key is None:
            self.error("Karşılaştırmada en az bir alan olmalı (ör. rsi<30).", start)
        return self.count(Compare(left, op, right))

    def count(self, node: Node) -> Node:
        self.conditions += 1
        if self.conditions > MAX_CONDITIONS:
            self.error(f"Bir taramada en fazla {MAX_CONDITIONS} koşul olabilir.", 0)
        return node

    def operand(self) -> Operand:
        t = self.tok
        if t.kind == "number":
            self.i += 1
            return Operand(None, t.value)
        if t.kind != "name" or t.value in KEYWORDS:
            self.error("Burada bir alan ya da sayı bekleniyordu.")
        self.i += 1
        name, param = t.value, None
        shortcut = re.fullmatch(r"(ema|sma)(\d+)", name)
        if shortcut and name not in F.FIELDS:
            name, param = shortcut.group(1), float(shortcut.group(2))
        if name not in F.FIELDS and name not in F.ALIASES:
            close = difflib.get_close_matches(name, list(F.FIELDS) + list(F.ALIASES), n=1, cutoff=0.6)
            hint = f" '{close[0]}' mi demek istediniz?" if close else " Alanlar: /tara_alanlar"
            self.error(f"'{name}' bilinmeyen alan.{hint}", t.pos)
        name = F.ALIASES.get(name, name)
        if name in ("kirdi_yukari", "kirdi_asagi"):
            self.error(f"{name} bir koşuldur: {name}({'direnc' if name == 'kirdi_yukari' else 'destek'}) yazın.", t.pos)
        if name == "egim":
            return self.slope(t)
        if self.tok.kind == "lparen" and F.FIELDS[name].param is not None:
            self.i += 1
            number = self.take("number", f"{name}(...) içinde bir sayı bekleniyordu: {name}(14).")
            if number.value != int(number.value) or not PARAM_RANGE[0] <= number.value <= PARAM_RANGE[1]:
                self.error(f"Parametre {PARAM_RANGE[0]} ile {PARAM_RANGE[1]} arasında bir tam sayı olmalı.", number.pos)
            self.take("rparen", f"{name}(...)'ı ')' ile kapatın.")
            param = number.value
        if param is not None and F.FIELDS[name].param is None:
            self.error(f"'{name}' parametre almaz.", t.pos)
        if name in ("ema", "sma") and param is not None and int(param) not in MA_PERIODS:
            self.error(f"{name}({int(param)}) desteklenmiyor; geçerli değerler: "
                       f"{', '.join(str(p) for p in MA_PERIODS)}.", t.pos)
        key = F.key(name, None if param is None else int(param))
        self.fields.add(key)
        return Operand(key)

    def slope(self, t) -> Operand:
        """egim(<field>, <n>): the field's change over n sessions, % (K-47)."""

        usage = "egim(alan, seans) yazın, ör. egim(sma200,21)."
        self.take("lparen", usage)
        inner = self.operand()
        if inner.key is None:
            self.error("egim(...) içinde bir alan olmalı, sayı değil. " + usage, t.pos)
        self.take("comma", usage)
        number = self.take("number", usage)
        if number.value != int(number.value) or not PARAM_RANGE[0] <= number.value <= PARAM_RANGE[1]:
            self.error(f"Seans sayısı {PARAM_RANGE[0]} ile {PARAM_RANGE[1]} arasında bir tam sayı olmalı.", number.pos)
        self.take("rparen", usage)
        key = f"egim({inner.key},{int(number.value)})"
        self.fields.add(key)
        return Operand(key)

    def option(self) -> bool:
        t = self.tok
        if t.kind != "name" or self.tokens[self.i + 1].kind != "assign":
            return False
        name = {"sira": "sirala", "siralama": "sirala"}.get(t.value, t.value)
        if name not in ("evren", "likidite", "sirala", "rejim", "ele", "ele_likidite", "ele_kurumsal", "ele_hareket",
                        "ele_veri"):
            return False
        self.i += 2
        value = self.tok
        if name in ("likidite", "ele_likidite"):
            number = self.take("number", f"{name}=15 gibi milyon TL olarak yazın (0 = kapalı).")
            if number.value < 0:
                self.error("Likidite tabanı negatif olamaz.", number.pos)
            self.options[name] = float(number.value)
            return True
        if name.startswith("ele"):
            switch = {"evet": True, "hayir": False, "1": True, "0": False}
            word = str(self.tok.value if self.tok.kind == "name" else _number(self.tok.value)) \
                if self.tok.kind in ("name", "number") else ""
            if word not in switch:
                self.error(f"{name}= sonrasına evet/hayir ya da 1/0 yazın.", value.pos)
            self.i += 1
            self.options[name] = switch[word]
            return True
        word = self.take("name", f"{name}= sonrasına bir seçenek yazın.").value
        word = {"guc": "goreli_guc"}.get(word, word) if name == "sirala" else word
        allowed = {"evren": UNIVERSES, "rejim": tuple(REGIMES)}.get(name, ORDERS)
        if word not in allowed:
            self.error(f"Bilinmeyen {name} '{word}'; seçenekler: {', '.join(allowed)}.", value.pos)
        self.options[name] = word
        return True


def parse(text: str) -> Query:
    normal = normalize(text)
    if len(normal) > MAX_LENGTH:
        raise ScreenError(f"İfade en fazla {MAX_LENGTH} karakter olabilir ({len(normal)} yazıldı).")
    return _Parser(normal).query()


__all__ = ["DEFAULT_LIQUIDITY", "MAX_CONDITIONS", "MAX_LENGTH", "ORDERS", "UNIVERSES", "Query", "ScreenError",
           "normalize", "parse", "tokenize"]
