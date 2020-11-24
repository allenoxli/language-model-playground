r"""Tokenizer base class."""

import abc
import json
import os
import re
import unicodedata
from collections import Counter
from typing import ClassVar, Dict, List, Optional, Sequence

import lmp.path
import lmp.tknzr.util


class BaseTknzr(abc.ABC):
    r""":term:`Tokenizer` abstract base class.

    Provide basic functionality for text preprocessing, save and load
    preprocessing configurations.
    All tokenizers must inherit this base class.

    Parameters
    ==========
    is_uncased: bool
        When performing :py:meth:`lmp.tknzr.BaseTknzr.norm`, convert text into
        lowercase if ``is_uncased == True``.
    max_vocab: int
        Maximum :term:`vocabulary` size.
    min_count: int
        Minimum :term:`token` frequency for each token to be included in
        tokenizer's :term:`vocabulary`.
    tk2id: Dict[str, int], optional
        Token (a string) to id (an integer) lookup table.
        If ``tk2id is not None``, then initialize lookup table with ``tk2id``.
        Otherwise initialize lookup table with special tokens only.

    Attributes
    ==========
    bos_tk: ClassVar[str]
        Token which represents the begining of a text.
        Text will be prepended with ``bos_tk`` when encoded by
        :py:meth:`lmp.tknzr.BaseTknzr.enc`.
    bos_tkid: ClassVar[int]
        Token id of ``bos_tk``.
    eos_tk: ClassVar[str]
        Token which represents the end of a text.
        Text will be appended with ``eos_tk`` when encoded by
        :py:meth:`lmp.tknzr.BaseTknzr.enc`.
    eos_tkid: ClassVar[int]
        Token id of ``eos_tk``.
    file_name: ClassVar[str]
        Tokenizer's configuration output file name.
    id2tk: Dict[int, str]
        Id (an integer) to token (a string) lookup table.
    is_uncased: bool
        When performing :py:meth:`lmp.tknzr.BaseTknzr.norm`, convert text into
        lowercase if ``is_uncased == True``.
    max_vocab: int
        Maximum vocabulary size.
    min_count: int
        Minimum token frequency for each token to be included in tokenizer's
        vocabulary.
    pad_tk: ClassVar[str]
        Token which represents paddings of a text.
        Text may be appended with ``pad_tk`` when encoded by
        :py:meth:`lmp.tknzr.BaseTknzr.enc`.
    pad_tkid: ClassVar[int]
        Token id of ``pad_tk``.
    tk2id: Dict[str, int]
        Token (a string) to id (an integer) lookup table.
    tknzr_name: ClassVar[str]
        Display name for tokenizer on CLI.
        Used only for command line argument parsing.
    unk_tk: ClassVar[str]
        Token which represents unknown tokens in a text.
        Tokens in text may be replaced with ``unk_tk`` when encoded by
        :py:meth:`lmp.tknzr.BaseTknzr.enc`.
    unk_tkid: ClassVar[int]
        Token id of ``unk_tk``.

    Raises
    ======
    TypeError
        When parameters are not confront their respective type annotation.

    Examples
    ========
    >>> from typing import List
    >>> from lmp.tknzr import BaseTknzr
    >>> class SimpleTknzr(BaseTknzr):
    ...     def tknz(self, seq: str) -> List[str]:
    ...         return [seq]
    ...     def dtknz(self, tks: List[str]) -> str:
    ...         return ''.join(tks)
    >>> tknzr = SimpleTknzr(is_uncased=False, max_vocab=10, min_count=2)
    >>> tknzr.tknz('hello world')
    ['hello world']
    >>> tknzr.dtknz(['hello world'])
    'hello world'
    """
    bos_tk: ClassVar[str] = '[bos]'
    bos_tkid: ClassVar[int] = 0
    eos_tk: ClassVar[str] = '[eos]'
    eos_tkid: ClassVar[int] = 1
    file_name: ClassVar[str] = 'tknzr.json'
    pad_tk: ClassVar[str] = '[pad]'
    pad_tkid: ClassVar[int] = 2
    tknzr_name: ClassVar[str] = 'base'
    unk_tk: ClassVar[str] = '[unk]'
    unk_tkid: ClassVar[int] = 3

    def __init__(
            self,
            is_uncased: bool,
            max_vocab: int,
            min_count: int,
            *,
            tk2id: Optional[Dict[str, int]] = None,
    ):
        if not isinstance(is_uncased, bool):
            raise TypeError(f'`is_uncased` must be an instance of `bool`.')

        self.is_uncased = is_uncased
        self.max_vocab = max_vocab
        self.min_count = min_count

        # Load pre-trained vocabulary.
        if tk2id is not None:
            self.tk2id = tk2id
            self.id2tk = {v: k for k, v in tk2id.items()}
        # Initialize vocabulary with special tokens.
        else:
            self.id2tk = {}
            self.tk2id = {}

            for tk, tkid in [
                [self.__class__.bos_tk, self.__class__.bos_tkid],
                [self.__class__.eos_tk, self.__class__.eos_tkid],
                [self.__class__.pad_tk, self.__class__.pad_tkid],
                [self.__class__.unk_tk, self.__class__.unk_tkid],
            ]:
                self.tk2id[tk] = tkid
                self.id2tk[tkid] = tk

    def save(self, exp_name: str) -> None:
        r"""Save tokenizer configuration in JSON format.

        Save the trained tokenizer's configuration into JSON format and named
        it with :py:attr:`lmp.tknzr.BaseTknzr.file_name`.
        This method will create experiment path first if experiment path does
        not exist.

        Parameters
        ==========
        exp_name: str
            Training experiment name of the tokenizer.

        Raises
        ======
        FileExistsError
            When experiment path already exists but is not a directory.

        See Also
        ========
        lmp.tknzr.BaseTknzr.load

        Examples
        ========
        >>> from lmp.tknzr import BaseTknzr
        >>> tknzr = BaseTknzr(is_uncased=False, max_vocab=10, min_count=2)
        >>> tknzr.save('my_exp')
        """
        file_dir = os.path.join(lmp.path.EXP_PATH, exp_name)
        file_path = os.path.join(file_dir, self.__class__.file_name)

        if not os.path.exists(file_dir):
            os.makedirs(file_dir)

        elif not os.path.isdir(file_dir):
            raise FileExistsError(f'{file_dir} is not a directory.')

        with open(file_path, 'w', encoding='utf8') as output_file:
            json.dump(
                {
                    'is_uncased': self.is_uncased,
                    'max_vocab': self.max_vocab,
                    'min_count': self.min_count,
                    'tk2id': self.tk2id,
                },
                output_file,
                ensure_ascii=False
            )

    @classmethod
    def load(cls, exp_name: str):
        r"""Load tokenizer configuration from JSON file.

        Load pre-trained tokenizer using saved configuration.

        Parameters
        ==========
        exp_name: str
            Name of the existing experiment.

        Raises
        ======
        FileNotFoundError
            If file ``exp/exp_name/tknzr.json`` does not exist.
        JSONDecodeError
            If tokenizer configuration is not in JSON format.
        TypeError
            When ``exp_name`` is not an instance of ``str``.
        ValueError
            When ``exp_name`` is empty string.

        See Also
        ========
        lmp.tknzr.BaseTknzr.save

        Examples
        ========
        >>> from lmp.tknzr import BaseTknzr
        >>> tknzr = BaseTknzr.load('my_exp')
        """
        if not exp_name:
            raise ValueError('`exp_name` must be non-empty.')

        file_path = os.path.join(lmp.path.EXP_PATH, exp_name, cls.file_name)

        if not os.path.exists(file_path):
            # TODO: add run training tokenizer script hint
            raise FileNotFoundError(f'File {file_path} does not exist.')

        if os.path.isdir(file_path):
            # TODO: add remove dir and run training tokenizer script hint
            raise FileExistsError(f'{file_path} is a directory.')

        with open(file_path, 'r', encoding='utf-8') as input_file:
            return cls(**json.load(input_file))

    def norm(self, txt: str) -> str:
        r"""Perform normalization on text.

        text will first be normalized using :py:func:`lmp.tknzr.util.norm`.
        If ``self.is_uncased == True``, then output text will be converted into
        lowercase.

        Parameters
        ==========
        txt: str
            Text to be normalized.

        Returns
        =======
        str
            Normalized text.

        See Also
        ========
        lmp.tknzr.util.norm

        Examples
        ========
        >>> from lmp.tknzr import BaseTknzr
        >>> tknzr = BaseTknzr(is_uncased=True, max_vocab=10, min_count=2)
        >>> tknzr.norm('ABC')
        'abc'
        """
        norm_txt = lmp.tknzr.util.norm(txt)
        if self.is_uncased:
            return norm_txt.lower()
        return norm_txt

    @abc.abstractmethod
    def tknz(self, txt: str) -> List[str]:
        r"""Perform :term:`tokenization` on text.

        Text will first be normalized and then be tokenized.

        Parameters
        ==========
        txt: str
            Text to be tokenized.

        Raises
        ======
        NotImplementedError
            When subclass do not implement tokenization.

        Returns
        =======
        List[str]
            List of tokens tokenized from text.

        See Also
        ========
        lmp.tknzr.BaseTknzr.dtknz
        lmp.tknzr.BaseTknzr.norm
        """
        raise NotImplementedError(
            f'In class `{self.__class__.__name__}`: '
            'method `tknz` not implemented yet.'
        )

    @abc.abstractmethod
    def dtknz(self, tks: Sequence[str]) -> str:
        r"""Convert :term:`tokens` back to one and only one text.

        Tokens will first be normalized and then be detokenized.

        Parameters
        ==========
        tks: Seqeuence[str]
            Sequence of tokens to be detokenized.

        Raises
        ======
        NotImplementedError
            When subclass do not implement detokenization.

        Returns
        =======
        str
            Text detokenized from tokens.

        See Also
        ========
        lmp.tknzr.BaseTknzr.tknz
        lmp.tknzr.BaseTknzr.norm
        """
        raise NotImplementedError(
            f'In class `{self.__class__.__name__}`: '
            'method `dtknz` not implemented yet.'
        )

    def enc(self, txt: str, *, max_seq_len: Optional[int] = -1) -> List[int]:
        r"""Encode text into sequence of token ids.

        Text will first be tokenized using :py:meth:`lmp.tknzr.BaseTknzr.tknz`,
        then format as follow::

            [bos] tk_1 tk_2 [unk] tk_4 ... tk_n [eos] [pad] ... [pad]

        1. ``[bos]`` denote "begin of sentence", ``[eos]`` denote
           "end of sentence", ``[pad]`` denote "padding of sentence" and
           ``[unk]`` denote "unknown tokens".

        2. Both ``[bos]`` and ``[eos]`` will be added.

        3. If added tokens sequence is longer than ``max_seq_len``, then it
           will be truncate to has length ``max_seq_len``.
        4. If added tokens sequence is shorter than ``max_seq_len``, then
           ``[pad]`` will be added util tokens sequence has length
           ``max_seq_len``.
        5. If some tokens in sequence is not in tokenizer's vocabulary, then
           they will be replaced with ``[unk]``.
        6. All tokens will be converted to token ids and returned.

        Parameters
        ==========
        txt: str
            Text to be encoded.
        max_seq_len: int, optional
            Truncate and pad token ids sequence to maximum sequence length.
            If ``max_seq_len == -1``, then token ids sequence will neither
            be truncated nor be padded.
            Defaults to ``-1``

        Returns
        =======
        List[int]
            Encoded token ids.

        See Also
        ========
        lmp.tknzr.BaseTknzr.dec
        lmp.tknzr.BaseTknzr.tknz
        lmp.tknzr.util.pad_to_max
        lmp.tknzr.util.trunc_to_max
        """
        # Prepend `[bos]` token id.
        tkids = [self.__class__.bos_tkid]

        # Convert tokens into token ids.
        for tk in self.tknz(txt):
            try:
                tkids.append(self.tk2id[tk])
            # Convert unknown tokens into `[unk]` token id.
            except KeyError:
                tkids.append(self.unk_tkid)

        # Append `[eos]` token id.
        tkids.append(self.__class__.eos_tkid)

        # First truncate sequence to maximum sequence length, then pad sequence
        # to maximum sequence length.
        return lmp.tknzr.util.pad_to_max(
            lmp.tknzr.util.trunc_to_max(tkids, max_seq_len=max_seq_len),
            self.__class__.pad_tkid,
            max_seq_len=max_seq_len
        )

    def dec(
            self,
            tkids: Sequence[int],
            *,
            rm_sp_tks: Optional[bool] = False
    ) -> str:
        r"""Decode sequence of token ids back to text.

        Sequence of token ids will first be converted to sequence tokens, and
        then be detokenized using :py:meth:`lmp.tknzr.BaseTknzr.dtknz`.

        Special tokens (``[bos]``, ``[eos]``, ``[pad]``) will be removed if
        ``rm_sp_tks == True``.
        Unknown tokens ``[unk]`` will not be removed even if
        ``rm_sp_tks == True``.
        If some token ids in sequence are not in tokenizer's inverse lookup
        vocabulary, then they will be converted into ``[unk]`` token.

        Parameters
        ==========
        tkids : Sequence[int]
            Sequence of token ids to be decoded.
        rm_sp_tks : bool, optional
            Whether to remove special tokens.
            If ``rm_sp_tks == True``, then remove ``[bos]``, ``[eos]`` and
            ``[pad]``.
            Defaults to ``False``.

        Returns
        =======
        str
            Decoded text.

        See Also
        ========
        lmp.tknzr.BaseTknzr.enc

        Note
        ====
        Unknown tokens cannot be converted back to original tokens, so unknown
        tokens should not be removed and serve as a hint of :term:`OOV`.
        """
        # Remove special token ids.
        if rm_sp_tks:
            sp_tkids = [
                self.__class__.bos_tkid,
                self.__class__.eos_tkid,
                self.__class__.pad_tkid,
            ]
            tkids = filter(lambda tkid: tkid not in sp_tkids, tkids)

        tks = []
        # Convert token ids into tokens.
        for tkid in tkids:
            try:
                tks.append(self.id2tk[tkid])
            # Convert unknown token ids into `[unk]` token.
            except KeyError:
                tks.append(self.__class__.unk_tk)

        return self.dtknz(tks)

    def batch_enc(
            self,
            batch_txt: Sequence[str],
            *,
            max_seq_len: int = -1
    ) -> List[List[int]]:
        r"""Encode batch of text into batch of sequences of token ids.

        Each text in ``batch_txt`` will be encoded with
        :py:meth:`lmp.tknzr.BaseTknzr.enc`.
        All encoded sequence of token ids will have same length.

        If ``max_seq_len == -1``, then ``max_seq_len`` will be set to the
        longest encoded sequence in ``batch_txt``.

        Parameters
        ==========
        batch_txt: Sequence[str],
            Batch of text to be encoded.
        max_seq_len: int, optional
            Truncate and pad each token ids sequence to maximum sequence
            length.
            If ``max_seq_len == -1``, then ``max_seq_len`` will be set to the
            longest encoded sequence in ``batch_txt``.
            Defaults to ``-1``

        Returns
        =======
        List[List[int]]
            Encoded batch of sequence of token ids.

        See Also
        ========
        lmp.tknzr.BaseTknzr.batch_dec
        lmp.tknzr.BaseTknzr.enc
        lmp.tknzr.util.pad_to_max
        lmp.tknzr.util.trunc_to_max
        """
        batch_tkids = [self.enc(txt, max_seq_len=-1) for txt in batch_txt]

        # If `max_seq_len == -1`, then `max_seq_len` is the longest sequence
        # length in the batch.
        if max_seq_len == -1:
            max_seq_len = max(map(len, batch_tkids))

        # Truncate each token ids sequence in batch to maximum sequence length.
        batch_tkids = [
            lmp.tknzr.util.trunc_to_max(tkids, max_seq_len=max_seq_len)
            for tkids in batch_tkids
        ]

        # Pad each token ids sequence in batch to maximum sequence length.
        return [
            lmp.tknzr.util.pad_to_max(
                tkids,
                self.__class__.pad_tkid,
                max_seq_len=max_seq_len
            )
            for tkids in batch_tkids
        ]

    def batch_dec(
            self,
            batch_tkids: Sequence[Sequence[int]],
            rm_sp_tks: bool = False
    ) -> List[str]:
        r"""Decode batch of sequences of token ids back to batch of text.

        Each sequence of token ids in `batch_tkids` will be decoded with
        :py:meth:`lmp.tknzr.BaseTknzr.dec`.

        Parameters
        ==========
        batch_tkids: Sequence[Sequence[int]]
            Batch of sequences of token ids to be decoded.
        rm_sp_tks: bool, optional
            Whether to remove special tokens.
            See :py:meth:`lmp.tknzr.BaseTknzr.dec` for the usage of ``rm_sp_tks``.
            Defaults to ``False``.

        Returns
        =======
        List[str]
            Batch of decoded text.

        See Also
        ========
        lmp.tknzr.BaseTknzr.batch_enc
        lmp.tknzr.BaseTknzr.dec
        """
        # Decode each sequence of token ids in the batch.
        return [self.dec(tkids, rm_sp_tks=rm_sp_tks) for tkids in batch_tkids]

    def build_vocab(self, batch_txt: Sequence[str]) -> None:
        """Build :term:`vocabulary` for tokenizer.

        Build :term:`vocabulary` based on :token:term frequency.
        Vocabulary is sorted by :term:`token` frenquency in descending
        order.

        If a token is going to add to vocabulary, then its token id will be the
        largest token id + 1.
        If a token's frequency is lower than ``self.min_count``, then that
        token will not be included in the vocabulary.
        If a token is already vocabulary, then it will not be included in
        vocabulary again.
        If the size of the vocabulary already ``>= self.max_vocab``, then
        no new tokens will be added.

        Parameters
        ==========
        batch_txt: Sequence[str]
            Source of text to build vocabulary.

        Returns
        =======
        None
        """
        # Count each token's frequency.
        c = Counter()
        for txt in batch_txt:
            c.update(self.tknz(self.norm(txt)))

        max_id = max(self.tk2id.values()) + 1
        for tk, tk_count in c.most_common():
            # Stop adding tokens when pass vocabulary size limit.
            if max_id >= self.max_vocab:
                break

            # Stop adding the token when the token frequency is low.
            # Since we sort token by frequency, the rest of tokens will not
            # have frequency higher than `self.min_count` and thus we can
            # break loop savely.
            if tk_count < self.min_count:
                break

            # Skip the token if already exists.
            if tk in self.tk2id:
                continue

            # Add token to vocabulary.
            self.tk2id[tk] = max_id
            self.id2tk[max_id] = tk
            max_id += 1

    @property
    def vocab_size(self) -> int:
        r""":term:`Vocabulary` size of tokenizer.

        Returns
        =======
        int
            Size of tokenizer's vocabulary.
        """
        return len(self.tk2id)