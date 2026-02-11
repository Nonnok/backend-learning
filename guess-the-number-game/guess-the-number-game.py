import random

# --- 関数 ---
# 入力値のチェック
def input_num(prompt, min_num = None, max_num = None):
    while True:
        try:
            num = int(input(prompt))

        except ValueError:
            print('注意：入力値エラーです。半角数字を入力してください。')
            continue

        if num <= 0:
            print('注意：0より大きい値を入力してください。')
            continue

        if min_num is not None and num < min_num:
            print(f'注意：{min_num}以上の値を入力してください。')
            continue

        if max_num is not None and num > max_num:
            print(f'注意：{max_num}以下の値を入力してください。')
            continue

        else:
            return num


# ヒント表示
def show_hint(production, answer):
    if production > answer:
        return print('（ヒント）あなたの予想は乱数より大きいです')
    else:
        return print('（ヒント）あなたの予想は乱数より小さいです')
# --- 関数end ---


print('''
--- 数字当てゲーム！ ---
最大値、最小値、試行回数を入力して、ゲームに挑戦してください。
注意：入力ルール
- 最小値：正の数
- 最大値：最小値以上の数
- 試行回数：最小値と最大値の範囲内
''')

# ユーザの入力
min_num = input_num('> 最小値を入力してください：')
max_num = input_num('> 最大値を入力してください：', min_num)
try_num = input_num('> 試行回数を入力してください：', min_num, max_num)
# 乱数の生成
random_num = random.randint(min_num, max_num)

# ゲーム
print(
  '-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-\n',
  f'数字当てゲームスタート！試行回数は{try_num}回です。\n',
  '-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-'
)


for i in range(1, try_num + 1):
    prediction = input_num(f'> {min_num}〜{max_num}の間で数字を予想してください：', min_num, max_num)
    if prediction == random_num:
        print(f'【GameClear】おめでとうございます！乱数は{random_num}でした。')
        break
    if i == try_num:
      print(f'【GameEnd】お疲れ様でした。生成された乱数は{random_num}でした。')
    else:
        print(f'予想が外れました。残りの試行回数は{try_num - i}です。')
        show_hint(prediction, random_num)