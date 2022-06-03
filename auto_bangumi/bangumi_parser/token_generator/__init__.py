delimiters = ["[", "]", " - ", "  "]


class TokenGenerator:
    def _get_tokens(self, name):
        tokens = []
        cursor = 0
        start = 0

        def append_token(n: str, c: int, s: int, step: int = 1) :
            token = n[s:c]
            token = token.strip()
            tokens.append(token)
            c += step
            s = c
            return c, s

        while cursor <= len(name):
            for t in delimiters:
                step = len(t)
                if name[cursor : cursor + step] == t:
                    if start < cursor:
                        # 前一个token完结
                        cursor, start = append_token(name, cursor, start, step)
                    else:
                        assert start == cursor
                        start += step
                        cursor += step
                    break
            else:
                if cursor == len(name):
                    # 最后一个
                    if start < cursor:
                        cursor, start = append_token(name, cursor, start)
                        break
                cursor += 1
        return tokens

    def generate(self, s):
        tokens = self._get_tokens(s)
        return tokens
