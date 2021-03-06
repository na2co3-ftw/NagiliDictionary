#!/usr/bin/ruby
# coding: utf-8


require 'cgi'
require 'pp'
require 'nagili_material/utilities'
require 'nagili_material/word'
require 'nagili_material/mana'
require 'nagili_material/request'


class NagiliOnline

  def initialize(cgi)
    @cgi = cgi
  end

  def run
    begin
      mode = @cgi.params["mode"][0].read rescue @cgi["mode"]
      case mode
      when "search"
        search
      when "prepare_request"
        prepare_request
      when "add_requests", "request"
        add_requests
      when "control"
        control
      when "edit_word", "edit"
        edit_word
      when "delete_requests", "delete"
        delete_requests
      when "import_word_data", "import", "update"
        import_word_data
        create_word_data(true)
        create_mana_data(true)
        change_due_date(true)
      when "create_word_data", "dictionary"
        create_word_data
      when "create_mana_data", "mana"
        create_mana_data
      when "display_patuu_function", "patuu"
        display_patuu_function
      when "debug"
        debug
      else
        default
      end
    rescue => exception
      error(exception.message + "\n" + exception.backtrace.join("\n"))
    end
  end

  def default
    print(Source.html_header)
    print(Source.header)
    print(Source.default)
    print(Source.footer)
  end

  def prepare_request
    print(Source.html_header)
    print(Source.header)
    print(Source.request_default)
    print(Source.footer)
  end

  def search
    password = @cgi["password"]
    type = @cgi["type"].to_i
    type_mana = @cgi["type_mana"].to_i
    agree = @cgi["agree"].to_i
    search = @cgi["search"]
    search_mana = @cgi["search_mana"]
    random = @cgi["random"].to_i
    page = @cgi["page"].to_i
    submit = @cgi["submit_mana"] == ""
    html = ""
    word_dictionary = WordDictionary.new
    mana_dictionary = ManaDictionary.new
    if submit
      matched, suggested = word_dictionary.search(search, type, agree)
    else
      matched, suggested = mana_dictionary.search(search_mana, type_mana)
    end
    number = matched.size
    if random == 1
      new_matched = matched.dup
      matched = (0...number).map{new_matched.slice!(rand(new_matched.size))}
    end
    unless suggested.empty?
      html << "<div class=\"suggest\">\n" 
      suggested.each do |word, suggest_type|
        html << "<span class=\"maybe\">もしかして:</span>"
        html << Source.word_link_html(password, word.name)
        html << " の#{suggest_type}?<br>\n"
      end
      html << "</div>\n\n"
    end
    new_password = (password == Utilities.password) ? password : nil
    if submit
      matched[page * 30, 30].each do |word|
        html << Source.result_word_html(new_password, word)
      end
    else
      matched[page * 30, 30].each do |mana|
        html << Source.result_mana_html(mana)
      end
    end
    if page > 0
      left = Source.word_link_html(password, search, type, agree, page - 1, "◀")
    else
      left = "◀"
    end
    if page * 30 + 30 < number
      right = Source.word_link_html(password, search, type, agree, page + 1, "▶")
    else
      right = "▶"
    end
    first_page = page - 5
    last_page = page + 5
    html << "<div class=\"number\">\n"
    html << "#{left}"
    html << "<span class=\"fraction\"><span class=\"page\">"
    (first_page..last_page).each do |current_page|
      if current_page < 0 || current_page > (number - 1) / 30
        html << "<span class=\"number\"></span>"
      else
        if page == current_page
          html << "<span class=\"number\">#{current_page + 1}</span>"
        else
          html << Source.word_link_html(password, search, type, agree, current_page, (current_page + 1).to_s)
        end
      end
    end
    html << "</span><span class=\"total\">"
    html << "<span class=\"number\">#{number / 30 + 1} <span class=\"small\">pages</span></span>　|　<span class=\"number\">#{number} <span class=\"small\">words</span></span></span></span>"
    html << "#{right}\n"
    html << "</div>\n\n"
    print(Source.html_header)
    print(Source.header(password, search, type, agree, random, search_mana, type_mana, submit))
    print(html)
    print(Source.footer)
  end

  def add_requests
    password = @cgi["password"]
    requests = @cgi["requests"]
    html = ""
    manager = RequestManager.new
    number = manager.add_requests(requests.split("\n"))
    html << "<div class=\"suggest\">\n"
    html << "造語依頼 (#{number} 件) が完了しました。<br>\n"
    html << "ご協力ありがとうございます。<br>\n"
    html << "</div>\n"
    print(Source.html_header)
    print(Source.header(password))
    print(html)
    print(Source.footer)
  end

  def control
    password = @cgi["password"]
    html = ""
    if password == Utilities.password
      manager = RequestManager.new
      requests = manager.requests
      html << "<div class=\"suggest\">\n"
      html << "<form action=\"nagili.cgi\" method=\"post\" enctype=\"multipart/form-data\">\n"
      html << "<input type=\"file\" name=\"file\">&nbsp;&nbsp;<input type=\"submit\" value=\"更新\"></input>\n"
      html << "<input type=\"hidden\" name=\"mode\" value=\"update\"></input>\n"
      html << "<input type=\"hidden\" name=\"password\" value=\"#{password}\"></input>\n"
      html << "</form>\n"
      html << "</div>\n"
      html << "<div class=\"suggest\">\n"
      html << "<form action=\"nagili.cgi\">\n"
      html << "<input type=\"submit\" value=\"辞典データ編集\"></input> (試験運用中)\n"
      html << "<input type=\"hidden\" name=\"mode\" value=\"edit\"></input>\n"
      html << "<input type=\"hidden\" name=\"password\" value=\"#{password}\"></input>\n"
      html << "</form>\n"
      html << "</div>\n"
      html << "<div class=\"suggest\">\n"
      html << "<form action=\"nagili.cgi\" method=\"post\">\n"
      html << "<input type=\"hidden\" name=\"mode\" value=\"delete\"></input><input type=\"hidden\" name=\"password\" value=\"#{password}\"></input>\n"
      html << "<input type=\"submit\" value=\"選択項目を削除\"></input>\n"
      (0..(requests.size / 100)).each do |i|
        sliced_requests = requests[i * 100, 100]
        html << "<table class=\"request\">\n"
        (0...50).each do |j|
          if j <= sliced_requests.size - 1
            request = sliced_requests[j].html_escape
            html << "<tr>"
            html << "<td class=\"left-number\"><input type=\"checkbox\" name=\"delete\" value=\"#{i * 100 + j},#{request}\"></input> #{i * 100 + j + 1}.</td>"
            html << "<td class=\"left-request\">#{request}</td>"
            if j + 50 <= sliced_requests.size - 1
              request = sliced_requests[j + 50].html_escape
              html << "<td class=\"right-number\"><input type=\"checkbox\" name=\"delete\" value=\"#{i * 100 + j + 50},#{request}\"></input> #{i * 100 + j + 51}.</td>"
              html << "<td class=\"right-request\">#{request}</td>"
            else
              html << "<td class=\"right-number\"></td><td class=\"right-request\"></td>"
            end
            html << "</tr>\n"
          end
        end
        html << "</table>\n"
        html << "<input type=\"submit\" value=\"選択項目を削除\"></input>\n"
      end
      html << "</div>\n"
    else
      html << "<div class=\"suggest\">\n"
      html << "パスワードが違います。<br>\n"
      html << "</div>\n"
    end
    print(Source.html_header)
    print(Source.header(password))
    print(html)
    print(Source.footer)
  end

  def edit_word
    password = @cgi["password"]
    type = (@cgi["type"] != "") ? @cgi["type"].intern : :default
    name = @cgi["name"] || ""
    meaning = @cgi["meaning"] || ""
    synonym = @cgi["synonym"] || ""
    ethymology = @cgi["ethymology"] || ""
    mana = @cgi["mana"] || ""
    usage = @cgi["usage"] || ""
    example = @cgi["example"] || ""
    html = ""
    log = ""
    dictionary = WordDictionary.new
    if password == Utilities.password
      case type
      when :load
        data = dictionary.search_strictly(name)
        if data.empty?
          log << "指定した単語は存在しません。\n"
          meaning, synonym, ethymology, mana, usage, example = "", "", "", "", "", ""
        else
          word = data[0]
          type = :save
          meaning, synonym, ethymology, mana, usage, example = word.meaning, word.synonym, word.ethymology, word.raw_mana, word.usage, word.example
        end
      when :save
        data = [name, meaning, synonym, ethymology, mana, usage, example]
        word = Word.new(*data.map{|s| s.gsub(/\r\n/, "\n").strip})
        result = dictionary.modify_word(word)
        if result
          log << "単語データ #{name} を保存しました。\n"
        else
          log << "単語データ #{name} は存在しません。\n"
        end
        type = :load
        meaning, synonym, ethymology, mana, usage, example = "", "", "", "", "", ""
      when :delete
        result = dictionary.delete_word_by_name(name)
        if result
          log << "単語データ #{name} を削除しました。\n"
        else
          log << "単語データ #{name} が存在しません。\n"
        end
        type = :load
        meaning, synonym, ethymology, mana, usage, example = "", "", "", "", "", ""
      end
      html << "<div class=\"suggest\">\n"
      html << "<form action=\"nagili.cgi\" method=\"post\">\n"
      html << "<table>\n"
      html << "<tr><td>単語:</td><td><input type=\"text\" name=\"name\" value=\"#{name.html_escape}\" size=\"40\"></input></td></tr>\n"
      html << "<tr><td>訳語:</td><td><textarea name=\"meaning\" cols=\"80\" rows=\"3\">#{meaning.html_escape}</textarea></td></tr>\n"
      html << "<tr><td>関連語:</td><td><textarea name=\"synonym\" cols=\"80\" rows=\"2\">#{synonym.html_escape}</textarea></td></tr>\n"
      html << "<tr><td>語源:</td><td><input type=\"text\" name=\"ethymology\" value=\"#{ethymology.html_escape}\" size=\"50\"></input></td></tr>\n"
      html << "<tr><td>京極:</td><td><input type=\"text\" name=\"mana\" value=\"#{mana.html_escape}\" size=\"50\"></input></td></tr>\n"
      html << "<tr><td>語法:</td><td><textarea name=\"usage\" cols=\"80\" rows=\"6\">#{usage.html_escape}</textarea></td></tr>\n"
      html << "<tr><td>用例:</td><td><textarea name=\"example\" cols=\"80\" rows=\"3\">#{example.html_escape}</textarea></td></tr>\n"
      html << "</table>\n"
      html << "<input type=\"radio\" name=\"type\" value=\"load\"#{(type == :load || type == :default) ? " checked" : ""}></input>読込　<input type=\"radio\" name=\"type\" value=\"save\"#{(type == :save) ? " checked" : ""}></input>保存　<input type=\"radio\" name=\"type\" value=\"delete\"#{(type == :delete) ? " checked" : ""}></input>削除　<input type=\"submit\" value=\"実行\"></input>\n"
      html << "<input type=\"hidden\" name=\"mode\" value=\"edit\"></input><input type=\"hidden\" name=\"password\" value=\"#{password}\"></input>\n"
      html << "</table>\n"
      html << "</form>\n"
      html << "</div>\n"
      html << "\n"
      html << "<div class=\"suggest\">\n"
      html << log
      html << "</div>\n"
    else
      html << "<div class=\"suggest\">\n"
      html << "パスワードが違います。<br>\n"
      html << "</div>\n"
    end
    print(Source.html_header)
    print(Source.header(password))
    print(html)
    print(Source.footer)
  end

  def delete_requests
    password = @cgi["password"]
    html = ""
    if password == Utilities.password
      manager = RequestManager.new
      delete_data = @cgi.params["delete"]
      requests = delete_data.map do |data|
        fixed_data = data.split(",", 2)
        fixed_data[0] = fixed_data[0].to_i
        next fixed_data
      end
      number = manager.delete_requests(requests)
      html << "<div class=\"suggest\">\n"
      if number
        html << "造語依頼データ (#{number} 件) を削除しました。"
      else
        html << "エラーが発生しました。<br>\n"
        html << "削除項目の選択中に、別のユーザーが他の項目を削除した可能性があります。もう一度やり直してください。\n"
      end
      html << "<form action=\"nagili.cgi\">\n"
      html << "<input type=\"submit\" value=\"戻る\"></input>\n"
      html << "<input type=\"hidden\" name=\"mode\" value=\"control\"></input>\n"
      html << "<input type=\"hidden\" name=\"password\" value=\"#{password}\"></input>\n"
      html << "</form>\n"
      html << "</div>\n"
    else
      html << "<div class=\"suggest\">\n"
      html << "パスワードが違います。<br>\n"
      html << "</div>\n"
    end
    print(Source.html_header)
    print(Source.header(password))
    print(html)
    print(Source.footer)
  end

  def import_word_data
    password = @cgi.params["password"][0].read
    html = ""
    if password == Utilities.password
      data = @cgi.params["file"][0].read
      size = Utilities.import_word_data(data)
      html << "<div class=\"suggest\">\n"
      html << "辞書のアップロード (#{size / 1024}KB) が完了しました。"
      html << "<form action=\"nagili.cgi\">\n"
      html << "<input type=\"submit\" value=\"戻る\"></input>\n"
      html << "<input type=\"hidden\" name=\"mode\" value=\"control\"></input>\n"
      html << "<input type=\"hidden\" name=\"password\" value=\"#{password}\"></input>\n"
      html << "</form>\n"
      html << "</div>\n"
    else
      html << "<div class=\"suggest\">\n"
      html << "パスワードが違います。<br>\n"
      html << "</div>\n"
    end
    print(Source.html_header)
    print(Source.header(password))
    print(html)
    print(Source.footer)
  end

  def create_word_data(create_only = false)
    Utilities.create_word_data
    Utilities.create_suggestable_names
    unless create_only
      print(Source.html_header(false))
      print("done")
    end
  end

  def create_mana_data(create_only = false)
    Utilities.create_mana_data
    unless create_only
      print(Source.html_header(false))
      print("done")
    end
  end

  def change_due_date(create_only = false)
    Utilities.change_due_date
    unless create_only
      print(Source.html_header(false))
      print("done: #{date_string}")
    end
  end

  def display_patuu_function
    output = ""
    output << "【 白雲項 コマンド一覧 】\n"
    output << "\n"
    output << "◆ 単語検索\n"
    output << "｜＊反応文字列: 単語検索\n"
    output << "｜・かぎカッコ内の文字列を単語検索します。ラテン文字表記でもハングル表記でも京極表記でも大丈夫。\n"
    output << "｜・ツイート内に「詳細」や「詳しく」を含めておくと最初から詳細をツイートします。ただし、最初の項目しか表示されません。\n"
    output << "├-◆ 凪霧辞典URL表示\n"
    output << "｜ ｜＊反応文字列: URL, アドレス\n"
    output << "｜ ｜・検索結果ツイートに対してリプライすると、凪霧辞典へのURLが返されます。\n"
    output << "｜ ◆ 詳細表示\n"
    output << "｜ ｜＊反応文字列: 詳細, 詳しく\n"
    output << "｜ ｜＊ツイート例: @panwan_patuu 2番目の結果を詳しく\n"
    output << "｜ ｜・検索結果ツイートに対してリプライすると、訳語の詳細をツイートします。\n"
    output << "｜ ｜・リプライに数字を含めておくと、その番号番目の単語データの詳細を返します。数字がない場合は最初のデータの詳細を返します。\n"
    output << "\n"
    output << "◆ 訳語検索\n"
    output << "｜＊反応文字列: 訳語検索\n"
    output << "｜・かぎカッコ内の文字列を訳語検索します。\n"
    output << "├-◆ 不足単語の造語依頼\n"
    output << "｜ ｜＊反応文字列: はい, うん, お願い\n"
    output << "｜ ｜・ヒット数が0件の場合は造語依頼するか尋ねられるので、それにリプライすると造語依頼します。\n"
    output << "｜ ◆ 凪霧辞典URL表示\n"
    output << "｜ ｜＊反応文字列: URL, アドレス\n"
    output << "｜ ｜・検索結果ツイートに対してリプライすると、凪霧辞典へのURLが返されます。\n"
    output << "｜ ｜・リプライに数字を含めておくと、その番号番目の単語データを表示する URL を返します。数字がない場合は最初のデータの URL を返します。\n"
    output << "\n"
    output << "◆ 造語依頼\n"
    output << "｜＊反応文字列: 依頼\n"
    output << "｜・かぎカッコ内の文字列を造語依頼します。\n"
    output << "｜・複数の造語依頼を行いたい場合は、単語をコンマか読点で区切ってください。\n"
    output << "\n"
    output << "◆ 依頼削除 (要権限)\n"
    output << "｜＊反応文字列: 依頼&削除\n"
    output << "｜・かぎカッコ内の文字列を造語依頼から削除します。\n"
    output << "｜・複数の削除を行いたい場合は、単語をコンマか読点で区切ってください。\n"
    output << "\n"
    output << "◆ 単語修正 (要権限)\n"
    output << "｜＊反応文字列: 修正, 編集\n"
    output << "｜＊ツイート例: @panwan_patuu 「kolu」の訳語を修正したい\n"
    output << "｜・かぎカッコ内で指定された単語の一部分を修正します。\n"
    output << "｜・必ずツイート内に「訳語」「関連語」「語源」「京極」「語法」「用例」のうちどれかを含めるようにしてください。\n"
    output << "├-◆ 単語修正\n"
    output << "｜ ｜＊反応文字列: ――\n"
    output << "｜ ｜・修正する内容を呟くよう促されるので、そのツイートにリプライする形で内容を呟いてください。リプライ先IDを除いたツイート全体が辞書データに書き込まれます。\n"
    output << "｜ ｜・末尾に「続く」と書いておくと、続くリプライも連続させて認識します。\n"
    output << "｜ ｜・改行の位置は、実際に改行するのではなく「\\」(バックスラッシュ)か「¥」で指定してください。\n"
    output << "｜ ｜・自動的にバックアップを取ります。\n"
    output << "\n"
    output << "◆ 単語削除 (要権限)\n"
    output << "｜＊反応文字列: 削除\n"
    output << "｜・かぎカッコ内で指定された単語を削除します。\n"
    output << "\n"
    output << "◆ 新規造語 (要権限)\n"
    output << "｜＊反応文字列: 造語\n"
    output << "｜・新しく単語データを追加します。\n"
    output << "├-◆ 新規造語\n"
    output << "｜ ｜＊反応文字列: ――\n"
    output << "｜ ｜・データ内容を呟くよう促されるので、そのツイートにリプライする形で内容を呟いてください。リプライ先IDを除いたツイート全体が辞書データに書き込まれます。\n"
    output << "｜ ｜・末尾に「続く」と書いておくと、続くリプライも連続させて認識します。\n"
    output << "｜ ｜・改行の位置は、実際に改行するのではなく「\\」(バックスラッシュ)か「¥」で指定してください。\n"
    output << "｜ ｜・自動的にバックアップを取ります。\n"
    output << "\n"
    output << "◆ 単語数\n"
    output << "｜＊反応文字列: 単語数\n"
    output << "｜・現在の凪霧辞典に登録されている単語の個数をリプライします。\n"
    output << "\n"
    output << "◆ 最近の造語依頼\n"
    output << "｜＊反応文字列: 最近&依頼\n"
    output << "｜・直近5件の造語依頼と合計依頼件数をリプライします。\n"
    output << "｜・ツイートに「ランダム」を含めておくと、直近の5件ではなくランダムに5件を選んでリプライします。\n"
    output << "\n"
    output << "◆ CSV\n"
    output << "｜＊反応文字列: CSV\n"
    output << "｜・現在の凪霧辞典の CSV データの URL をリプライします。\n"
    output << "\n"
    output << "◆ バージョン\n"
    output << "｜＊反応文字列: バージョン\n"
    output << "｜・現在の凪霧辞典システム全体のバージョン番号と状態をリプライします。デバッグ用です。\n"
    output << "\n"
    output << "◆ 起床 (睡眠時のみ)\n"
    output << "｜＊反応文字列: 起きて\n"
    output << "｜・寝てるときでも起こします。起こすと30分間だけ起きて処理を行い、また寝ます。\n"
    output << "\n"
    output << "◆ 緊急停止 (要権限)\n"
    output << "｜＊反応文字列: 緊急停止\n"
    output << "｜・botの機能を全て停止します。停止するとTwitter上でのやり取りではもとに戻せません。というかそれ以降一切反応しなくなります。\n"
    output << "｜・項が何かもうどうしようもないことをしていた場合は、このコマンドを送信してZiphilに知らせてください。\n"
    output << "\n"
    output << "◆ お気に入り\n"
    output << "｜＊反応文字列: ――\n"
    output << "｜・以上のコマンドの範囲にないツイートはお気に入りに登録されます。\n"
    output << "｜・リプライもお気に入りもされない場合は、以下の原因が考えられます。\n"
    output << "｜  ・一度に処理するリプライ(6件)から外れた → 次回の稼働時に処理されるはず\n"
    output << "｜  ・リプライが多いためにTwitterAPIが読み込む件数(20件くらい)からも外れてしまった → 諦めて\n"
    output << "｜  ・訳語検索などで指定されたフォーマットになっていない(かぎカッコを忘れるなど) → もう一度試してください\n"
    output << "｜  ・内部エラー → やばい\n"
    output << "\n"
    output << "・特殊権限: @Ziphil, @ayukawamay, @na2co3_ftw, @Faras_Tilasos\n"
    output << "\n"
    output << "・リプライの処理間隔は5分です。\n"
    output << "・一度に処理できるリプライは6件までです。6件以上のリプライが溜まっていた場合は、古いものから6件のみを処理します。\n"
    output << "・リプライに対してさらにリプライを送ることで行われる処理は、24時間以上空くと反応されなくなります。\n"
    output << "・0時から1時の間に寝て、7時から8時の間に起きます。寝てから起きるまでの間は特に処理を行いません。\n"
    output << "・辞書データは毎日4時10分にバックアップが取られます。最大15ファイルまで保存します。\n"
    output << "\n"
    print(Source.html_header(false))
    print(output)
  end

  def debug
  end

  def error(message)
    html = ""
    html << "<div class=\"suggest\">\n"
    html << message.html_escape.gsub("\n", "<br>\n")
    html << "</div>\n"
    print(Source.html_header)
    print(Source.header)
    print(html)
    print(Source.footer)
  end

end


module Source;extend self

  def html_header(type = true)
    html = ""
    if type
      html << "Content-Type: text/html\n\n"
    else
      html << "Content-Type: text/plain; charset=utf-8\n\n"
    end
    return html
  end

  def header(password = "", search = "", type = 0, agree = 0, random = 0, search_mana = "", type_mana = 0, submit = true)
    html = ""
    html << "<!DOCTYPE html>\n"
    html << "<html lang=\"ja\">\n"
    html << "<head>\n"
    html << "<meta charset=\"UTF-8\">\n"
    html << "<link rel=\"stylesheet\" type=\"text/css\" href=\"../style/nagili.css\">\n"
    html << "<script src=\"library/jquery.js\"></script>\n"
    html << "<script src=\"nagili_material/cgi.js\"></script>\n"
    html << "<title>凪霧辞典</title>\n"
    html << "</head>\n"
    html << "<body onload=\"document.search_form.#{(submit) ? "search" : "search_mana"}.select()\">\n"
    html << "\n"
    html << "<div class=\"main\">\n"
    html << "\n"
    html << "<div class=\"menu\">\n"
    html << "\n"
    html << "<a class=\"title\" href=\"nagili.cgi\">\n"
    html << "<img src=\"nagili_material/top.png\">"
    html << "</a>\n"
    html << "<div class=\"version\">git: #{Utilities.version}</div>"
    html << "\n"
    html << "<div class=\"search\">\n"
    html << "<form action=\"nagili.cgi\" name=\"search_form\">\n"
    html << "<span class=\"small\">凪日:</span> <input type=\"text\" name=\"search\" value=\"#{search.html_escape}\"></input>&nbsp;&nbsp;<input type=\"submit\" name=\"submit\" value=\"検索\"></input><br>\n"
    html << "<input type=\"radio\" name=\"type\" value=\"0\"#{(type == 0) ? " checked" : ""}></input>単語　<input type=\"radio\" name=\"type\" value=\"1\"#{(type == 1) ? " checked" : ""}></input>訳語　<input type=\"radio\" name=\"type\" value=\"3\"#{(type == 3) ? " checked" : ""}></input>全文<br>\n"
    html << "<input type=\"radio\" name=\"agree\" value=\"0\"#{(agree == 0) ? " checked" : ""}></input>完全一致　<input type=\"radio\" name=\"agree\" value=\"1\"#{(agree == 1) ? " checked" : ""}></input>部分一致<br>\n"
    html << "<input type=\"checkbox\" name=\"random\" class=\"random\" value=\"1\"#{(random == 1) ? " checked" : ""}></input>ランダム表示<br>\n"
    html << "<input type=\"hidden\" name=\"mode\" value=\"search\"></input><input type=\"hidden\" name=\"password\" value=\"#{password}\"></input>\n"
    html << "<div class=\"margin\"></div>\n"
    html << "<span class=\"small\">京極:</span> <input type=\"text\" name=\"search_mana\" value=\"#{search_mana.html_escape}\"></input>&nbsp;&nbsp;<input type=\"submit\" name=\"submit_mana\" value=\"検索\"></input><br>\n"
    html << "<input type=\"radio\" name=\"type_mana\" value=\"0\"#{(type_mana == 0) ? " checked" : ""}></input>京極　<input type=\"radio\" name=\"type_mana\" value=\"1\"#{(type_mana == 1) ? " checked" : ""}></input>読み<br>\n"
    html << "</form>\n"
    html << "</div>\n"
    html << "<div class=\"search\">\n"
    html << "<form action=\"nagili.cgi\" class=\"request\">\n"
    html << "<input type=\"submit\" value=\"造語依頼\"></input><br>\n"
    html << "<input type=\"hidden\" name=\"mode\" value=\"prepare_request\"></input>\n"
    html << "</form>\n"
    html << "</div>\n"
    html << "\n"
    html << "</div>\n"
    html << "\n"
    html << "<div class=\"content\">\n\n"
    return html
  end

  def footer
    html = ""
    html << "\n"
    html << "</div>\n"
    html << "\n"
    html << "</div>\n"
    html << "\n"
    html << "</body>\n"
    html << "</html>\n"
    return html
  end

  def default
    html = ""
    html << "<div class=\"suggest\">\n"
    html << "<a href=\"https://sites.google.com/site/nagilikuli/home\" target=\"blank\">人工言語凪霧</a>のオンライン辞典です。<br>\n"
    html << "<br>\n"
    html << "・凪霧とは<br>\n"
    html << "人工言語凪霧(なぎり)は、架空世界で使われている言葉です。<br>\n"
    html << "人工言語アルカと同じ世界で用いられていて、凪霧に対してアルカは外国語という関係にあります。<br>\n"
    html << "凪霧では自分たちの言語をnagili(ナギリ)と言い、これに凪霧という漢字を当てています。<br>\n"
    html << "このサイトにおいては基本的に凪霧という呼び方をしていますが、アルカではアルティア語と呼ぶことがあります。<br>\n"
    html << "この2つは同じ意味で用いられます。<br>\n"
    html << "<br>\n"
    html << "・製作者/連絡先<br>\n"
    html << "凪霧は、基礎部分を seren arbazard、文法の詳細や語彙などを mei felixian が主に製作しています。<br>\n"
    html << "質問等はTwitterアカウントで mei felixian (@ayukawamay) が受け付けております。<br>\n"
    html << "また、このオンライン辞書は Ziphil Shaleiras (@Ziphil) が作成しました。<br>\n"
    html << "辞書に関する不具合や質問に関しては、こちらへお願いします。<br>\n"
    html << "<br>\n"
    html << "・ソースコード<br>\n"
    html << "凪霧辞典プロジェクト (オンライン凪霧辞典, 凪霧辞典bot, 白雲項) のソースコードは<a href=\"https://github.com/Ziphil/NagiliDictionary\" target=\"blank\">GitHub</a>上で公開されています。"
    html << "</div>\n"
    return html
  end

  def request_default
    html = ""
    html << "<div class=\"suggest\">\n"
    html << "こちらのフォームから不足している単語を依頼できます。<br>\n"
    html << "別々の単語はそれぞれ改行し、1行に1単語になるようにお書きください。<br>\n"
    html << "<form action=\"nagili.cgi\">\n"
    html << "<textarea name=\"requests\" cols=\"70\" rows=\"10\"></textarea><br>\n"
    html << "<input type=\"submit\" value=\"造語依頼\"></input><br>\n"
    html << "<input type=\"hidden\" name=\"mode\" value=\"request\"></input>\n"
    html << "</form>\n"
    html << "</div>\n"
    return html
  end

  def result_word_html(password, word)
    html = ""
    html << "<div class=\"word\">\n"
    html << "<h1><table>\n"
    html << "<tr>"
    html << "<td class=\"mana\">#{word.mana}</td>"
    html << "<td class=\"yula\">#{word.name.to_hangeul}</td>"
    html << "<td class=\"hacm\">#{(word.reading == "") ? word.name : word.reading}</td>"
    html << "</tr>\n"
    html << "<tr>"
    html << "<td class=\"kanji\">#{word.mana}</td>"
    html << "<td class=\"hangeul\">#{word.name.to_hangeul}</td>"
    html << "<td class=\"latin\">#{(word.reading == "") ? word.name : word.reading}</td>"
    html << "</tr>\n"
    html << "</table></h1>\n"
    meaning = word.meaning.gsub("\"\"", "\"").html_escape
    meaning.each_line do |line|
      if word_class = Utilities::WORD_CLASSES.select{|s, _| line.include?(s)}.to_a[0]
        new_line = line.chomp
        new_line.gsub!(/［(.+?)］/){"<span class=\"box\">#{$~[1]}</span>"}
        new_line.gsub!(/〔(.+?)〕/){"<span class=\"genre\">#{$~[1]}</span>"}
        new_line.gsub!(/&lt;(.+?)&gt;/){"<span class=\"tag\">〈#{$~[1]}〉</span>"}
        new_line.gsub!("、", "、<wbr>")
        html << "<div class=\"#{word_class[1]}\">" + new_line + "</div>\n"
      end
    end
    synonym = word.synonym
    synonym.each_line do |line|
      new_line = line.chomp
      new_line.gsub!(/((([a-z]\s*)+[、]*)+)/){$~[1].split("、").map{|s| Source.word_link_html(password, s)}.join("、")}
      new_line.gsub!(/［(.+)］/){"<span class=\"bracket\">#{$~[1]}</span>"}
      new_line.gsub!("、", "、<wbr>")
      html << "<div class=\"synonym\">" + new_line + "</div>\n"
    end
    ethymology = word.ethymology
    unless ethymology == ""
      html << "<div class=\"information\">" + ethymology.html_escape.chomp + "</div>\n"
    end
    usage = word.usage.gsub("\"\"", "\"").html_escape
    unless usage == ""
      usage.gsub!(/［(.+)］/){"<span class=\"small\">［#{$~[1]}］</span>"}
      usage.gsub!("\n", "<br>\n")
      html << "<div class=\"usage\">\n" + usage + "</div>\n"
    end
    example = word.example.gsub("\"\"", "\"").html_escape
    unless example == ""
      example.gsub!(/【(.+)】/){"<span class=\"small\">【#{$~[1]}】</span>"}
      example.gsub!("\n", "<br>\n")
      example.gsub!(/^(.+)(\.|\!|\?)/) do
        sentence = $~[1]
        punctuation = $~[2]
        next sentence.split(" ").map{|s| Source.word_link_html(password, s).gsub("\">", "\" class=\"example\">")}.join(" ") + punctuation
      end
      html << "<div class=\"usage\">\n" + example + "</div>\n"
    end
    if password
      html << "<div class=\"usage\">\n"
      html << "<a href=\"nagili.cgi?mode=edit&type=load&name=#{word.unique_name.html_escape}&password=#{password.html_escape}\">編集</a>\n"
      html << "</div>\n"
    end
    html << "</div>\n\n"
    return html
  end

  def result_mana_html(mana)
    html = ""
    html << "<div class=\"mana-word\">\n"
    html << "<div class=\"left\">\n"
    html << "<span class=\"mana\">#{mana.name}</span>\n"
    html << "字形編集<br>\n"
    html << "</div>\n"
    html << "<div class=\"right\">\n"
    html << "<table>\n"
    html << "<tr><td>文字コード: </td><td>#{mana.code}</td>\n"
    html << "<tr><td>部首: </td><td>#{mana.radical}</td>\n"
    html << "<tr><td>画数: </td><td>#{mana.stroke_count} 画</td>\n"
    html << "<tr><td>読み: </td><td>#{mana.readings.join(", ")}</td>\n"
    html << "<tr><td>特殊読み: </td><td>#{mana.special_readings.map{|s, t| s + " → " + t.join(", ")}.join("<br>")}</td>\n"
    html << "</table>\n"      
    html << "</div>\n"
    html << "<div class=\"clear\"></div>"
    html << "</div>\n"
    return html
  end

  def word_link_html(password, search, type = 0, agree = 0, page = 0, text = nil)
    html = "<a href=\"nagili.cgi?mode=search&search=#{search.url_escape}&type=#{type}&agree=#{agree}&page=#{page}&password=#{password}\">"
    html << (text || search)
    html << "</a>"
    return html
  end

end


if RUBY_VERSION >= "1.9.0"
  Encoding.default_external = "UTF-8"
else
  $KCODE = "U"
end

NagiliOnline.new(CGI.new).run