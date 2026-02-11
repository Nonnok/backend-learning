import sys

# 入力ガイド
def show_guide( process ):
    print('［！］入力内容に誤りがあります')
    match process:
        case 'reverse' | 'copy' | 'duplicate-contents' | 'replace-string':
            print(f'--- {process}の構文 ---')
        case _:
            print(
                f'処理 {process} は存在しません。\nこのプログラムは【reverse】, 【copy】, 【duplicate-contents】, 【replace-string】を実行することができます。'
                )

    match process:
        case 'reverse':
            print(f'python3 file_manipulator.py {process}', '内容を反転したいファイルのパス 反転した内容を出力したいファイルのパス')
        case 'copy':
            print(f'python3 file_manipulator.py {process}', 'コピーしたいファイルのパス コピーを出力するファイルのパス')
        case 'duplicate-contents':
            print(f'python3 file_manipulator.py {process}', '内容を複製したいファイルのパス 複製する回数（半角数字）')
        case 'replace-string':
            print(f'python3 file_manipulator.py {process}', '置き換えを実行したいファイルのパス 置き換えたい文字列 置き換える文字列')
    sys.exit(1)


# 引数バリデーション
def check_arguments( input_command ):
    process = input_command[1]
    match process:
        case 'reverse' | 'copy' | 'duplicate-contents':
            if len( input_command ) != 4:
                show_guide( process )
        case 'replace-string':
            if len( input_command ) != 5:
                show_guide( process )
        case _:
                show_guide( process )

# 処理内容の分岐
def execution_process( input_command ):
    process = input_command[1]
    match process:
        case 'reverse':
            reverse( input_command[2], input_command[3] )
        case 'copy':
            copy( input_command[2], input_command[3] )
        case 'duplicate-contents':
            duplicate_contents( input_command[2], input_command[3] )
        case 'replace-string':
            replace_string( input_command[2], input_command[3], input_command[4] )


# ファイル読み込み処理
def read_file( file_path ):
    try:
      with open( file_path ) as file:
        return file.read()
    except FileNotFoundError:
        print( f'{ file_path } は存在しません' )
        sys.exit(1)

# ファイル書き込み処理
def write_file( file_path, contents ):
    with open( file_path, 'w' ) as file:
        return file.write( contents )

# 逆順出力
def reverse( source_path, output_path ):
    contents = read_file( source_path )
    contents = contents[::-1]
    write_file( output_path, contents )


# ファイルコピー
def copy( source_path, output_path ):
    contents = read_file( source_path )
    write_file( output_path, contents )


# 複製・上書き
def duplicate_contents( source_path, num ):
    # 複製回数の数値バリデーション
    try:
        num = int(num)
    except ValueError:
        print( '複製回数には1以上の半角数字を入力してください' )
        sys.exit(1)
    if num <= 0:
        print( '複製回数には、1以上の自然数を入力してください。' )
        sys.exit(1)

    contents = read_file( source_path )
    contents *= num + 1
    write_file( source_path, contents )


# 文字列置き換え
def replace_string( source_path, current_str, replace_str ):
    contents = read_file( source_path )

    if contents.find( current_str ) == -1:
        print( f'文字列「{current_str}」は{source_path}内に存在しないため、置き換え処理ができません' )
        sys.exit(1)
    else:
        contents = contents.replace( current_str, replace_str )
        write_file( source_path, contents )

# 入力を受け取る
input_command = sys.argv

# 前提バリデーション
if len( input_command ) < 2:
    print( '入力値が不足しています' )
    sys.exit(1)

# バリデーション
check_arguments( input_command )
# 処理実行
execution_process( input_command )
print( '処理は正常に終了しました' )