#!/usr/bin/ruby
# coding: utf-8

# /usr/bin/ruby C:/Ruby187/bin/ruby.exe


$KCODE = "U"

require 'cgi'
require 'pp'
require 'material/nagili_utilities'
require 'material/twitter'


class NagiliDictionary;include NagiliUtilities

  def initialize(cgi)
    @cgi = cgi
    @password = ""
    load_password
  end

  def run
    begin
      mode = @cgi.params["mode"][0].read rescue @cgi["mode"]
      case mode
      when "search"
        search
      when "request_default"
        request_default
      when "request"
        request
      when "control"
        control
      when "delete"
        delete
      when "update"
        update
        create_mana_data(true)
        change_due_date(true)
      when "twitter"
        create_twitter_data
      when "mana"
        create_mana_data
      when "patuu"
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

  def load_password
    @password = File.read("nagili/password.txt").strip
  end

  def default
    print_html_header
    print_header
    print_default
    print_footer
  end

  def request_default
    print_html_header
    print_header
    print_request_default
    print_footer
  end

  def search
    type = @cgi["type"].to_i
    type_mana = @cgi["type_mana"].to_i
    agree = @cgi["agree"].to_i
    search = @cgi["search"]
    search_mana = @cgi["search_mana"]
    random = @cgi["random"].to_i
    page = @cgi["page"].to_i
    submit = @cgi["submit_mana"] == ""
    html = ""
    if submit
      matched, suggested = NagiliUtilities.search_word(search, type, agree)
    else
      matched, suggested = NagiliUtilities.search_mana(search_mana, type_mana)
    end
    number = matched.size
    if random == 1
      new_matched = matched.dup
      matched = (0...number).map{new_matched.slice!(rand(new_matched.size))}
    end
    html << "<div class=\"suggest\">\n" unless suggested.empty?
    suggested.each do |word, suggest_type|
      html << "<span class=\"maybe\">もしかして:</span>"
      html << NagiliDictionary.word_link_html(word)
      html << " の#{suggest_type}?<br>\n"
    end
    html << "</div>\n\n" unless suggested.empty?
    if submit
      matched[page * 30, 30].each do |data|
        html << NagiliDictionary.result_html_word(*data)
      end
    else
      matched[page * 30, 30].each do |mana, words, double_words, nagili_data|
        html << NagiliDictionary.result_html_mana(mana, words, double_words)
        nagili_data.each do |data|
          html << NagiliDictionary.result_html_word(*data)
        end
      end
    end
    if page > 0
      left = NagiliDictionary.word_link_html(search, type, agree, page - 1, "◀")
    else
      left = "◀"
    end
    if page * 30 + 30 < number
      right = NagiliDictionary.word_link_html(search, type, agree, page + 1, "▶")
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
          html << NagiliDictionary.word_link_html(search, type, agree, current_page, (current_page + 1).to_s)
        end
      end
    end
    html << "</span><span class=\"total\">"
    html << "<span class=\"number\">#{number / 30 + 1} <span class=\"small\">pages</span></span>　|　<span class=\"number\">#{number} <span class=\"small\">words</span></span></span></span>"
    html << "#{right}\n"
    html << "</div>\n\n"
    print_html_header
    print_header(search, type, agree, random, search_mana, type_mana, submit)
    print(html)
    print_footer
  end

  def request
    requests = @cgi["requests"]
    html = ""
    number = NagiliUtilities.add_requests(requests.split("\n"))
    html << "<div class=\"suggest\">\n"
    html << "造語依頼 (#{number} 件) が完了しました。<br>\n"
    html << "ご協力ありがとうございます。<br>\n"
    html << "</div>\n"
    print_html_header
    print_header
    print(html)
    print_footer
  end

  def control
    html = ""
    requests = NagiliUtilities.requests_data
    if @cgi["password"] == @password
      html << "<div class=\"suggest\">\n"
      html << "<form action=\"nagili.cgi\" method=\"post\" enctype=\"multipart/form-data\">\n"
      html << "<input type=\"file\" name=\"file\">&nbsp;&nbsp;<input type=\"submit\" value=\"更新\"></input>\n"
      html << "<input type=\"hidden\" name=\"mode\" value=\"update\"></input>\n"
      html << "<input type=\"hidden\" name=\"password\" value=\"zkgburpdvq\"></input>\n"
      html << "</form>\n"
      html << "</div>\n"
      html << "<div class=\"suggest\">\n"
      html << "<form action=\"nagili.cgi\" method=\"post\">\n"
      html << "<input type=\"hidden\" name=\"mode\" value=\"delete\"></input><input type=\"hidden\" name=\"password\" value=\"zkgburpdvq\"></input>\n"
      html << "<input type=\"submit\" value=\"選択項目を削除\"></input>\n"
      html << "<ol>\n"
      requests.each_with_index do |request, i|
        html << "<li><input type=\"checkbox\" name=\"delete\" value=\"#{i},#{request.html_escape}\"></input>#{request.html_escape}</li>\n"
      end
      html << "</ol>\n"
      html << "<input type=\"submit\" value=\"選択項目を削除\"></input>\n"
      html << "</div>\n"
    else
      html << "<div class=\"suggest\">\n"
      html << "パスワードが違います。<br>\n"
      html << "</div>\n"
    end
    print_html_header
    print_header
    print(html)
    print_footer
  end

  def delete
    html = ""
    if @cgi["password"] == @password
      delete_data = @cgi.params["delete"]
      deletes = delete_data.map do |data|
        fixed_data = data.split(",", 2)
        fixed_data[0] = fixed_data[0].to_i
        next fixed_data
      end
      number = NagiliUtilities.delete_requests(deletes)
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
      html << "<input type=\"hidden\" name=\"password\" value=\"zkgburpdvq\"></input>\n"
      html << "</form>\n"
      html << "</div>\n"
    else
      html << "<div class=\"suggest\">\n"
      html << "パスワードが違います。<br>\n"
      html << "</div>\n"
    end
    print_html_header
    print_header
    print(html)
    print_footer
  end

  def update
    html = ""
    if @cgi.params["password"][0].read == @password
      file = @cgi.params["file"][0].read
      size = NagiliUtilities.save_dictionary_data(file)
      html << "<div class=\"suggest\">\n"
      html << "辞書のアップロード (#{size / 1024}KB) が完了しました。"
      html << "<form action=\"nagili.cgi\">\n"
      html << "<input type=\"submit\" value=\"戻る\"></input>\n"
      html << "<input type=\"hidden\" name=\"mode\" value=\"control\"></input>\n"
      html << "<input type=\"hidden\" name=\"password\" value=\"zkgburpdvq\"></input>\n"
      html << "</form>\n"
      html << "</div>\n"
    else
      html << "<div class=\"suggest\">\n"
      html << "パスワードが違います。<br>\n"
      html << "</div>\n"
    end
    print_html_header
    print_header
    print(html)
    print_footer
  end

  def create_mana_data(create_only = false)
    NagiliUtilities.create_mana_data
    unless create_only
      print_html_header(false)
      print("done")
    end
  end

  def change_due_date(create_only = false)
    due_time = Time.now + 604800
    date_string = due_time.strftime("%Y/%m/%d")
    File.open("nagili/due_date.txt", "w").print(date_string)
    unless create_only
      print_html_header(false)
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
    print_html_header(false)
    print(output)
  end

  def debug
    output = "done"
    ziphil = Twitter.new(:ziphil)
    ziphil.tweet("凪霧辞典がアレ。")
    print_html_header(false)
    pp(ziphil.oauth_data)
    print(output)
  end

  def show_mana_data
    single_mana = NagiliUtilities.single_mana_data
    double_mana = NagiliUtilities.double_mana_data
    output = ""
    output << "―― 2種類以上の読みがあるもの ――\n"
    single_mana.each do |mana, words|
      if words.size > 1
        output << "#{mana}: #{words.join(", ")}\n"
      end
    end
    output << "―― 1文字分の読みが抽出できなかったもの ――\n"
    double_mana.each do |mana, words|
      output << "#{mana}: #{words.join(", ")}\n"
    end
    output << "―― その他 ――\n"
    print_html_header(false)
    print(output)
  end

  def error(message)
    html = ""
    html << "<div class=\"suggest\">\n"
    html << message.html_escape.gsub("\n", "<br>\n")
    html << "</div>\n"
    print_html_header
    print_header
    print(html)
    print_footer
  end

  def print_html_header(html = true)
    if html
      print("Content-Type: text/html\n\n")
    else
      print("Content-Type: text/plain; charset=utf-8\n\n")
    end
  end

  def print_header(search = "", type = 0, agree = 0, random = 0, search_mana = "", type_mana = 0, submit = true)
    html = ""
    html << "<!DOCTYPE html>\n"
    html << "<html lang=\"ja\">\n"
    html << "<head>\n"
    html << "<meta charset=\"UTF-8\">\n"
    html << "<link rel=\"stylesheet\" type=\"text/css\" href=\"../style/nagili.css\">\n"
    html << "<script src=\"library/jquery.js\"></script>\n"
    html << "<script src=\"material/cgi.js\"></script>\n"
    html << "<title>凪霧辞典</title>\n"
    html << "</head>\n"
    html << "<body onload=\"document.search_form.#{(submit) ? "search" : "search_mana"}.select()\">\n"
    html << "\n"
    html << "<div class=\"main\">\n"
    html << "\n"
    html << "<div class=\"menu\">\n"
    html << "\n"
    html << "<a class=\"title\" href=\"nagili.cgi\">\n"
    html << "<img src=\"material/top.png\">"
    html << "</a>\n"
    html << "\n"
    html << "<div class=\"search\">\n"
    html << "<form action=\"nagili.cgi\" name=\"search_form\">\n"
    html << "<span class=\"small\">凪日:</span> <input type=\"text\" name=\"search\" value=\"#{search.html_escape}\"></input>&nbsp;&nbsp;<input type=\"submit\" name=\"submit\" value=\"検索\"></input><br>\n"
    html << "<input type=\"radio\" name=\"type\" value=\"0\"#{(type == 0) ? " checked" : ""}></input>単語　<input type=\"radio\" name=\"type\" value=\"1\"#{(type == 1) ? " checked" : ""}></input>訳語　<input type=\"radio\" name=\"type\" value=\"3\"#{(type == 3) ? " checked" : ""}></input>全文<br>\n"
    html << "<input type=\"radio\" name=\"agree\" value=\"0\"#{(agree == 0) ? " checked" : ""}></input>完全一致　<input type=\"radio\" name=\"agree\" value=\"1\"#{(agree == 1) ? " checked" : ""}></input>部分一致<br>\n"
    html << "<input type=\"checkbox\" name=\"random\" class=\"random\" value=\"1\"#{(random == 1) ? " checked" : ""}></input>ランダム表示<br>\n"
    html << "<input type=\"hidden\" name=\"mode\" value=\"search\"></input>\n"
    html << "<div class=\"margin\"></div>\n"
    html << "<span class=\"small\">京極:</span> <input type=\"text\" name=\"search_mana\" value=\"#{search_mana.html_escape}\"></input>&nbsp;&nbsp;<input type=\"submit\" name=\"submit_mana\" value=\"検索\"></input><br>\n"
    html << "<input type=\"radio\" name=\"type_mana\" value=\"0\"#{(type_mana == 0) ? " checked" : ""}></input>京極　<input type=\"radio\" name=\"type_mana\" value=\"1\"#{(type_mana == 1) ? " checked" : ""}></input>読み<br>\n"
    html << "</form>\n"
    html << "</div>\n"
    html << "<div class=\"search\">\n"
    html << "<form action=\"nagili.cgi\" class=\"request\">\n"
    html << "<input type=\"submit\" value=\"造語依頼\"></input><br>\n"
    html << "<input type=\"hidden\" name=\"mode\" value=\"request_default\"></input>\n"
    html << "</form>\n"
    html << "</div>\n"
    html << "\n"
    html << "</div>\n"
    html << "\n"
    html << "<div class=\"content\">\n\n"
    print(html)
  end

  def print_footer
    html = ""
    html << "\n"
    html << "</div>\n"
    html << "\n"
    html << "</div>\n"
    html << "\n"
    html << "</body>\n"
    html << "</html>\n"
    print(html)
  end

  def print_default
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
    html << "</div>\n"
    print(html)
  end

  def print_request_default
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
    print(html)
  end

  def self.result_html_word(word, meaning, synonym, ethymology, mana, usage, example)
    html = ""
    html << "<div class=\"word\">\n"
    word = word.gsub(/\(\d+\)/, "").strip
    if match = mana.match(/([a-z\s\[\]\/]*)\s*([^a-z\s\[\]\/]*)/)
      html << "<h1><table><tr>"
      html << "<td class=\"mana\">#{match[2]}</td>"
      html << "<td class=\"yula\">#{word.to_nagili_hangeul}</td>"
      html << "<td class=\"hacm\">#{(match[1] == "") ? word : match[1]}</td>"
      html << "</tr><tr>"
      html << "<td class=\"kanji\">#{match[2]}</td>"
      html << "<td class=\"hangeul\">#{word.to_nagili_hangeul}</td>"
      html << "<td class=\"latin\">#{(match[1] == "") ? word : match[1]}</td>"
      html << "</tr></table></h1>\n"
    else
      html << "<h1></h1>"
    end
    meaning.gsub!("\"\"", "\"")
    meaning = meaning.html_escape
    meaning.each_line do |line|
      if word_class = WORD_CLASSES.select{|s, _| line.include?(s)}.to_a[0]
        new_line = line.chomp
        new_line.gsub!(/［(.+?)］/){"<span class=\"box\">#{$1}</span>"}
        new_line.gsub!(/〔(.+?)〕/){"<span class=\"genre\">#{$1}</span>"}
        new_line.gsub!(/&lt;(.+?)&gt;/){"<span class=\"tag\">〈#{$1}〉</span>"}
        new_line.gsub!("、", "、<wbr>")
        html << "<div class=\"#{word_class[1]}\">" + new_line + "</div>\n"
      end
    end
    synonym.each_line do |line|
      new_line = line.chomp
      new_line.gsub!(/((([a-z]\s*)+[、]*)+)/){$1.split("、").map{|s| self.word_link_html(s)}.join("、")}
      new_line.gsub!(/［(.+)］/){"<span class=\"bracket\">#{$1}</span>"}
      new_line.gsub!("、", "、<wbr>")
      html << "<div class=\"synonym\">" + new_line + "</div>\n"
    end
    unless ethymology == ""
      html << "<div class=\"information\">" + ethymology.html_escape.chomp + "</div>\n"
    end
    usage.gsub!("\"\"", "\"")
    usage = usage.html_escape
    unless usage == ""
      usage.gsub!(/［(.+)］/){"<span class=\"small\">［#{$1}］</span>"}
      usage.gsub!("\n", "<br>\n")
      html << "<div class=\"usage\">\n" + usage + "</div>\n"
    end
    example.gsub!("\"\"", "\"")
    example = example.html_escape
    unless example == ""
      example.gsub!(/【(.+)】/){"<span class=\"small\">【#{$1}】</span>"}
      example.gsub!("\n", "<br>\n")
      example.gsub!(/^(.+)(\.|\!|\?)/) do
        sentence = $1
        punctuation = $2
        next sentence.split(" ").map{|s| self.word_link_html(s).gsub("\">", "\" class=\"example\">")}.join(" ") + punctuation
      end
      html << "<div class=\"usage\">\n" + example + "</div>\n"
    end
    html << "</div>\n\n"
    return html
  end

  def self.result_html_mana(mana, words, double_words)
    html = ""
    html << "<div class=\"mana-word\">\n"
    html << "<div class=\"left\">\n"
    html << "<span class=\"mana\">#{mana}</span>\n"
    html << "字形編集<br>\n"
    html << "</div>\n"
    html << "<div class=\"right\">\n"
    html << "<table>\n"
    html << "<tr><td>文字コード: </td><td>――</td>\n"
    html << "<tr><td>部首: </td><td>――</td>\n"
    html << "<tr><td>画数: </td><td>――</td>\n"
    html << "<tr><td>読み: </td><td>#{words.join(", ")}</td>\n"
    html << "<tr><td>特殊読み: </td><td>#{double_words.map{|s| s[0] + " → " + s[1].join(", ")}.join("<br>")}</td>\n"
    html << "</table>\n"      
    html << "</div>\n"
    html << "<div class=\"clear\"></div>"
    html << "</div>\n"
    return html
  end

  def self.word_link_html(word, type = 0, agree = 0, page = 0, text = nil)
    html = "<a href=\"nagili.cgi?mode=search&search=#{word.url_escape}&type=#{type}&agree=#{agree}&page=#{page}\">"
    displayed_text = (text) ? text : word
    html << displayed_text
    html << "</a>"
    return html
  end

end


NagiliDictionary.new(CGI.new).run