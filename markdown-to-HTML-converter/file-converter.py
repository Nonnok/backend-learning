import sys
import markdown

# --- 関数 ---
# ファイルの読み込み
def read_file(file_path):
    try:
        with open(file_path, encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        print(f'{ file_path } は存在しません')
        sys.exit(1)

# ファイルの書き込み
def write_file(file_path, contents):
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(contents)
    except Exception as e:
        print( f'ファイル書き込みエラー: { e }' )
        sys.exit(1)

# 処理の判定
def choice_process(input_command):
    process = input_command[1]
    inputfile = input_command[2]
    outputfile = input_command[3]
    if process == 'markdown':
        convert_md_to_html(inputfile, outputfile)
    else:
        print( f'処理{ process }は存在しないため、実行できません' )
        sys.exit(1)

# マークダウンファイル→HTMLファイル
def convert_md_to_html(inputfile, outputfile):
    contents = read_file(inputfile)
    html = markdown.markdown(contents)
    write_file(outputfile, html)
    print( f'{ inputfile }は{ outputfile }として書き出されました' )
# --- 関数end ---

input_command = sys.argv

if len(input_command) != 4:
    print(
        '-- 構文に従って入力してください--\n',
        'python3 file-converter.py markdown inputfile outputfile'
      )
    sys.exit(1)

choice_process(input_command)