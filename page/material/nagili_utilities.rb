# coding: utf-8


require 'nkf'


module NagiliUtilities;extend self

  WORD_CLASSES = {"［名詞］" => "noun", "［動詞］" => "verb", "［形容詞］" => "adjective", "［連体詞］" => "adjective", "［副詞］" => "adverb", "［感動詞］" => "interjection", "［接続詞］" => "conjunction",
                  "［助動詞］" => "verb", "［末動詞］" => "verb",
                  "［接続助詞］" => "particle", "［等位接続詞］" => "conjunction", "［文頭接続詞］" => "conjunction",
                  "［終助詞］" => "particle", "［格助詞］" => "particle", "［副助詞］" => "particle", "［係助詞］" => "particle",
                  "［接尾辞］" => "suffix", "［接頭辞］" => "suffix",
                  "［ユマナ］" => "noun", "［数詞］" => "noun", "［助数詞］" => "suffix"}
  SUGGESTED_CLASSES = ["［名詞］", "［動詞］", "［形容詞］", "［副詞］", "［助動詞］"]
  CONJUGATIVE_CLASSES = ["［動詞］", "［形容詞］", "［助動詞］"]
  MAIN_TAGS = ["［語法］", "［文化］", "［語義］"]
  WORD_TAGS = ["［類義語］", "［反意語］", "［対義語］", "［同義語］", "［一覧］"]
  EXAMPLE_TAGS = ["【用例】"]
  SUFFIXES = {"la" => "連用形", "li" => "名詞形", "le" => "命令形", "lo" => "仮定形", "lu" => "終止連体形", "lan" => "否定形", "lane" => "否定命令形", "lano" => "否定仮定形"}
  VOICES = {"" => "", "so" => "使役", "ju" => "受動", "an" => "丁寧", "mi" => "過去", "soju" => "使役受動", "soan" => "使役丁寧", "somi" => "使役過去", "juan" => "受動丁寧", "jumi" => "受動過去",
            "anmi" => "丁寧過去", "sojuan" => "使役受動丁寧", "sojumi" => "使役受動過去", "soanmi" => "使役丁寧過去", "juanmi" => "受動丁寧過去", "sojuanmi" => "使役受動丁寧過去"}

  # 辞書データから単語を検索します。
  # 検索結果とサジェスト結果の 2 つのデータを格納した配列を返します。
  def search_word(search, type, agree)
    dictionary = self.fixed_dictionary_data
    matched = []
    suggested = []
    conjugation = []
    alphabet_search = search.to_nagili_alphabet
    hangeul_search = search.to_nagili_hangeul
    SUFFIXES.each do |suffix, suffix_type|
      VOICES.each do |voice, voice_type|
        unless voice + suffix == "lu"
          if alphabet_search.match(/#{voice + suffix}$/)
            original_search = alphabet_search.gsub(/#{voice + suffix}$/, "lu")
            conjugation << [original_search, voice_type + suffix_type]
          end
        end
      end
    end
    dictionary.each do |data|
      word, meaning, synonym, ethymology, mana, usage, example = data
      word = word.gsub(/\(\d+\)/, "").strip
      if type == 0
        if agree == 0 || agree == 5
          if word == alphabet_search
            matched << data
          end
          if match = mana.match(/([^a-z\s\[\]\/]+)/)
            if match[1] == hangeul_search
              matched << data
            end
          end
          if agree < 5
            if word.match(/lu$/) && CONJUGATIVE_CLASSES.any?{|s| meaning.include?(s)}
              conjugation.each do |original_search, conjugation_type|
                if word == original_search
                  suggested << [word, conjugation_type]
                end
              end
            end
            if word.match(/\s/)
              word.split(/\s/).each do |element|
                if element == alphabet_search
                  dictionary.each do |sub_data|
                    if sub_data[0].gsub(/\(\d+\)/, "").strip == element
                      SUGGESTED_CLASSES.each do |sub_class|
                        if sub_data[1].include?(sub_class)
                          suggested << [word, "一部"]
                        end
                      end
                    end
                  end
                end
              end
            end
          end
        elsif agree == 1
          if word =~ /#{alphabet_search}/
            matched << data
          end
          if match = mana.match(/([^a-z\s\[\]\/]+)/)
            if match[1] =~ /#{hangeul_search}/
              matched << data
            end
          end
        end
      elsif type == 1
        if agree == 0
          meaning.each_line do |line|
            if line.gsub(/［(.+)］/, "").gsub(/<(.+)>/, "").split("、").map{|s| s.strip}.any?{|s| s == search}
              matched << data
            end
          end
        elsif agree == 1
          meaning.each_line do |line|
            if line.gsub(/［(.+)］/, "").gsub(/<(.+)>/, "").split("、").map{|s| s.strip}.any?{|s| s =~ /#{search}/}
              matched << data
            end
          end
        end
      elsif type == 3
        if data.join("\n") =~ /#{search}/
          matched << data
        end
      end
    end
    matched = matched.uniq.sort
    suggested = suggested.uniq.sort
    return [matched, suggested]
  end

  # 辞書データから京極を検索します。
  # 検索結果とサジェスト結果の 2 つのデータを格納した配列を返しますが、サジェスト結果を表す配列は必ず空になります。
  # 返される検索結果は、京極, 読み, 特殊読み, その読みに関連する凪霧辞典の単語データの順に格納された大きさ 4 の配列になります。
  def search_mana(search, type)
    dictionary = self.fixed_dictionary_data
    single_mana = self.single_mana_data
    double_mana = self.double_mana_data
    matched = []
    single_mana.each do |mana, words|
      search = search.to_nagili_alphabet
      if (type == 0 && mana == search) || (type == 1 && words.include?(search))
        double_words = []
        nagili_data = []
        double_mana.each do |other_mana, other_words|
          if other_mana.include?(mana)
            double_words << [other_mana, other_words]
          end
        end
        dictionary.each do |data|
          nagili_word = data[0].gsub(/\(\d+\)/, "").strip
          nagili_mana = data[4]
          words.each do |word|
            if (word == nagili_word || word + "lu" == nagili_word) && nagili_mana.match(/^([a-z\s\[\]\/]*)\s*#{mana}/)
              nagili_data << data
            end
          end
        end
        matched << [mana, words, double_words, nagili_data]
      end
    end
    matched = matched.uniq
    return [matched, []]
  end

  def search_word_strictly(search)
    dictionary = self.fixed_dictionary_data
    dictionary.each do |data|
      return [data] if search == data[0]
    end
    return []
  end

  def dictionary_data
    data = ""
    File.open("nagili/dictionary.csv", "r") do |file|
      data = file.read
    end
    data.gsub!(/\r\n?/, "\n")
    data.sub!(/.+\n/, "")
    dictionary = data.scan(/"(.*?)","(.*?)","(.*?)",(.*?),(.*?),(.*?),"(.*?)"\n/m)
    return dictionary
  end

  # CSV 形式の辞書データを読み込み、データを種類別に分け直します。
  # 各単語データは、単語, 語義, 関連語, 語源, 京極, 用法, 用例の順に格納された大きさ 7 の配列になります。
  def fixed_dictionary_data
    dictionary = self.dictionary_data
    new_dictionary = []
    dictionary.each do |data|
      word = data[0]
      meaning = ""
      synonym = ""
      ethymology = ""
      mana = ""
      usage = ""
      example = ""
      mana_flag = true
      ethymology_flag = true
      example_flag = false
      explanation = data[1] + "\n" + data[2]
      explanation.each_line do |line|
        if WORD_CLASSES.any?{|s, _| line.include?(s)}
          meaning << line
        elsif WORD_TAGS.any?{|s| line.include?(s)}
          synonym << line
        elsif MAIN_TAGS.any?{|s| line.include?(s)}
          usage << line
          example_flag = false
        elsif EXAMPLE_TAGS.any?{|s| line.include?(s)}
          example << line
          example_flag = true
        elsif ethymology_flag && (line.match(/\d+:.+/) || line.match(/^seren/))
          ethymology << line
          ethymology_flag = false
        elsif mana_flag && line.match(/([a-z\s\[\]\/]*)\s*([^a-z\s\[\]\/]*)/)
          mana << line
          mana_flag = false
        elsif example_flag
          example << line
        else
          usage << line
        end
      end
      new_dictionary << [word, meaning, synonym, ethymology, mana, usage, example]
    end
    return new_dictionary
  end

  def single_mana_data
    data = ""
    File.open("nagili/single_mana.txt", "r") do |file|
      data = file.read
    end
    single_mana = []
    data.each_line do |line|
      if match = line.match(/^(.+):\s*(.+)/)
        single_mana << [match[1], match[2].split(",")]
      end
    end
    return single_mana
  end

  def double_mana_data
    data = ""
    File.open("nagili/double_mana.txt", "r") do |file|
      data = file.read
    end
    double_mana = []
    data.each_line do |line|
      if match = line.match(/^(.+):\s*(.+)/)
        double_mana << [match[1], match[2].split(",")]
      end
    end
    return double_mana
  end

  def requests_data
    data = ""
    File.open("nagili/request.txt", "r") do |file|
      data = file.read
    end
    requests = data.split(/\r*\n/).reject{|s| s.match(/^\s*$/)}
    return requests
  end

  def password
    return File.read("nagili/password.txt").strip
  end

  # 辞典データからランダムにデータを取り出して、ツイッターで呟くためのテキストに変換して返します。
  # 自動的に 140 文字以下になるように調整されます。
  def random_tweet_text
    dictionary = self.dictionary_data
    data = dictionary[rand(dictionary.size)]
    output = ""
    word = data[0].gsub(/\(.+\)/, "").strip
    text = ""
    text << word + " ― "
    text << data[1].scan(/^\s*(［.+］.+)$/).to_a.delete_if{|s| !WORD_CLASSES.any?{|t, _| s[0].include?(t)}}.map{|s| s[0].gsub(/>\s*/, "> ")}.join(" / ")
    text = text.split(//u)[0...117].join("")
    output << text
    output << " http://nagili.minibird.jp/page/nagili.cgi?mode=search&search=#{word.url_escape}&type=0&agree=0"
    return output
  end

  # 造語依頼データをファイルに書き込みます。
  # 引数 requests には造語依頼データを格納した配列を渡してください。 
  # 正常にデータの書き込みが終了した場合は、依頼件数を返します。
  def add_requests(requests)
    data = requests.join("\n") + "\n"
    File.open("nagili/request.txt", "a") do |file|
      file.puts(data)
    end
    return requests.size
  end

  # 指定された造語依頼データをファイルから削除します。
  # 引数 deletes には、依頼データのインデックスと依頼データの内容の 2 つからなる配列を格納した配列を渡してください。
  # 正常にデータの削除が終了した場合は、依頼件数を返します。
  # インデックスと内容が一致していないなどの原因で削除を行わなかった場合は、nil を返します。
  def delete_requests(deletes)
    requests = self.requests_data
    deletes = deletes.sort_by{|s| s[0]}
    if deletes.all?{|s, t| requests[s] == t}
      deletes.reverse_each do |number, _|
        requests.delete_at(number)
      end
      File.open("nagili/request.txt", "w") do |file|
        file.puts(requests.join("\n"))
      end
      return deletes.size
    else
      return nil
    end
  end

  # 指定された造語依頼データをファイルから削除します。
  # 引数 deletes には、依頼データを格納した配列を渡してください。
  # 正常にデータの削除が終了した場合は、依頼件数を返します。
  def delete_requests_loosely(deletes)
    requests = self.requests_data
    deletes.each do |delete|
      requests.delete(delete)
    end
    File.open("nagili/request.txt", "w") do |file|
      file.puts(requests.join("\n"))
    end
    return deletes.size
  end

  # 辞書データを外部ファイルから読み込んでサーバー上に保存します。
  # データは自動的に文字コードを UTF-8 に変換して保存されます。
  # 正常にデータの保存が終了した場合は、データのバイト数を返します。
  def save_dictionary_data(data)
    data = NKF.nkf("-w", data)
    backup_dictionary_data
    File.open("nagili/dictionary.csv", "w") do |file|
      file.puts(data)
    end
    return data.length
  end

  # 辞書データのバックアップを取ります。
  # 正常にデータのバックアップが終了した場合は、データのバイト数を返します。
  def backup_dictionary_data(name = "temporary")
    time_string = Time.now.strftime("%Y%m%d%H%M%S")
    old_data = ""
    File.open("nagili/dictionary.csv", "r") do |file|
      old_data = file.read
    end
    File.open("nagili/backup/#{name}-#{time_string}.csv", "w") do |file|
      file.puts(old_data)
    end
    return old_data.length
  end

  # 辞書データをファイルに保存します。
  # 正常にデータの保存が終了した場合は、データのバイト数を返します。
  # 辞書データは自動的にバックアップが取られます。
  def update_dictionary_data(dictionary)
    output = "word,trans,exp,level,memory,modify,pron,filelink\n"
    dictionary.each do |data|
      word = data[0].gsub("\"\"", "\"").gsub("\"", "\"\"")
      translation = data[1].gsub("\"\"", "\"").gsub("\"", "\"\"")
      explanation = data[2].gsub("\"\"", "\"").gsub("\"", "\"\"")
      output << "\"#{word}\",\"#{translation}\",\"#{explanation}\",0,0,0,\"\"\n"
    end
    backup_dictionary_data
    File.open("nagili/dictionary.csv", "w") do |file|
      file.puts(output)
    end
    return output.length
  end

  # 辞書データに新しい単語データを追加し、ファイルに保存します。
  # 正常にデータの保存が終了した場合は、データのバイト数を返します。
  # 指定された単語がすでに登録されている場合は、単語の新規登録をせずに nil を返します。
  def add_dictionary_data(word, translation, explanation)
    dictionary = self.dictionary_data
    unless dictionary.any?{|s| s[0] == word}
      dictionary << [word, translation, explanation, 0, 0, 0, ""]
      return self.update_dictionary_data(dictionary)
    else
      return nil
    end
  end

  # 辞書データから単語データを削除します。
  # 正常にデータの保存が終了した場合は、データのバイト数を返します。  
  # 指定された単語が登録されていない場合は、単語の削除をせずに nil を返します。
  def delete_dictionary_data(word)
    dictionary = self.dictionary_data
    index = nil
    dictionary.each_with_index do |data, i|
      if data[0] == word
        index = i
        break
      end
    end
    if index
      dictionary.delete_at(index)
      return self.update_dictionary_data(dictionary)
    else
      return nil
    end
  end

  # 既存の辞書データを修正し、ファイルに保存します。
  # 引数に nil を指定すると、データの変更を行いません。
  # 正常にデータの保存が終了した場合は、データのバイト数を返します。
  # 指定された単語が登録されていない場合は、何の操作もせずに nil を返します。
  def modify_fixed_dictionary_data(word, meaning, synonym, ethymology, mana, usage, example)
    dictionary = self.dictionary_data
    fixed_dictionary = self.fixed_dictionary_data
    index = nil
    fixed_index = nil
    dictionary.each_with_index do |data, i|
      if data[0] == word
        index = i
        break
      end
    end
    fixed_dictionary.each_with_index do |data, i|
      if data[0] == word
        fixed_index = i
        break
      end
    end
    if index && fixed_index
      new_meaning = (meaning) ? meaning : fixed_dictionary[fixed_index][1]
      new_synonym = (synonym) ? synonym : fixed_dictionary[fixed_index][2]
      new_ethymology = (ethymology) ? ethymology : fixed_dictionary[fixed_index][3]
      new_mana = (mana) ? mana : fixed_dictionary[fixed_index][4]
      new_usage = (usage) ? usage : fixed_dictionary[fixed_index][5]
      new_example = (example) ? example : fixed_dictionary[fixed_index][6]
      new_translation = new_meaning.strip + "\n" + new_synonym.strip + "\n" + new_ethymology.strip + "\n" + new_mana.strip + "\n" + new_usage.strip
      new_translation = new_translation.gsub(/\n+/, "\n").strip
      new_example = new_example.strip
      dictionary[index] = [word, new_translation, new_example, 0, 0, 0, ""]
      return self.update_dictionary_data(dictionary)
    else
      return nil
    end
  end

  # 辞書データから京極の情報を抜き出し、外部ファイルに保存します。
  def create_mana_data
    dictionary = self.fixed_dictionary_data
    mana_data = []
    single_mana_data = Hash.new{|h, k| h[k] = []}
    double_mana_data = Hash.new{|h, k| h[k] = []}
    unknown_mana_data = Hash.new{|h, k| h[k] = []}
    single_output = ""
    double_output = ""
    unknown_output = ""
    dictionary.each do |data|
      word = data[0].gsub(/\(\d+\)/, "").gsub(" ", "").strip
      mana = data[4]
      unless word == "凡例"
        if match = mana.match(/([^a-z\s\[\]\/]+)/)
          mana_data << [word, match[1].to_nagili_alphabet]
        end
      end
    end
    mana_data = mana_data.map do |word, mana|
      new_word, new_mana = word, mana
      if match = mana.match(/^([a-z]+)/)
        if word.match(/^#{match[0]}/)
          new_word = word.gsub(/^#{match[0]}/, "")
          new_mana = mana.gsub(/^#{match[0]}/, "")
        end
      end
      if match = mana.match(/([a-z]+)$/)
        if word.match(/#{match[0]}$/)
          new_word = word.gsub(/#{match[0]}$/, "")
          new_mana = mana.gsub(/#{match[0]}$/, "")
        end
      end
      next [new_word, new_mana]
    end
    mana_data.delete_if{|s, t| s.match(/^\s*$/) && t.match(/^\s*$/)}
    mana_data.each do |word, mana|
      if mana.split(//).size == 1
        single_mana_data[mana] << word
      end
    end
    mana_data.delete_if do |word, mana|
      splited_mana = mana.split(//)
      if splited_mana.all?{|s| single_mana_data.key?(s)}
        splited_mana = splited_mana.map{|s| single_mana_data[s]}
        possible_reading = splited_mana[0].product(*splited_mana[1..-1]).map{|s| s.join("")}
        next possible_reading.any?{|s| word == s}
      else
        next false
      end
    end
    mana_data.each do |word, mana|
      unknown_mana_data[mana] << word
    end
    single_mana_data.sort.each do |mana, words|
      words = words.map{|s| (s.include?(s + "n")) ? s + "n" : s}
      words.uniq!
      single_output << "#{mana}: #{words.join(",")}\n"
    end
    double_mana_data.sort.each do |mana, words|
      words.uniq!
      double_output << "#{mana}: #{words.join(",")}\n"
    end
    unknown_mana_data.sort.each do |mana, words|
      words.uniq!
      unknown_output << "#{mana}: #{words.join(",")}\n"
    end
    File.open("nagili/single_mana.txt", "w") do |file|
      file.puts(single_output)
    end
    File.open("nagili/double_mana.txt", "w") do |file|
      file.puts(double_output)
    end
    File.open("nagili/unknown_mana.txt", "w") do |file|
      file.puts(unknown_output)
    end
  end

  def create_search_index
    dictionary = self.fixed_dictionary_data
    word_index = []
    meaning_index = Hash.new{|h, k| h[k] = []}
    word_output = ""
    meaning_output = ""
    dictionary.each do |data|
      word, meaning, _ = data
      word_index << word
      meaning.each_line do |line|
        line.gsub(/［(.+)］/, "").gsub(/<(.+)>/, "").split(/\s*、\s*/).each do |each_meaning|
          meaning_index[each_meaning.strip] << word
        end
      end
    end
    word_output << word_index.join("\n")
    meaning_index.each do |each_meaning, words|
      meaning_output << "#{each_meaning}: #{words.join(", ")}\n"
    end
    File.open("nagili/word.txt", "w") do |file|
      file.puts(word_output)
    end
    File.open("nagili/meaning.txt", "w") do |file|
      file.puts(meaning_output)
    end
  end

end


class String

  ALPHABET_TABLE = {"아" => "a", "에" => "e", "이" => "i", "오" => "o", "우" => "u", "야" => "ya", "예" => "ye", "요" => "yo", "위" => "yu",
                    "바" => "ba", "베" => "be", "비" => "bi", "보" => "bo", "부" => "bu", "뱌" => "bya", "볘" => "bye", "뵤" => "byo", "뷔" => "byu",
                    "다" => "da", "데" => "de", "디" => "di", "도" => "do", "두" => "du", "댜" => "dya", "뎨" => "dye", "됴" => "dyo", "뒤" => "dyu", 
                    "파" => "fa", "페" => "fe", "피" => "fi", "포" => "fo", "푸" => "fu", "퍄" => "fya", "폐" => "fye", "표" => "fyo", "퓌" => "fyu",
                    "가" => "ga", "게" => "ge", "기" => "gi", "고" => "go", "구" => "gu", "갸" => "gya", "계" => "gye", "교" => "gyo", "귀" => "gyu",
                    "하" => "ha", "헤" => "he", "히" => "hi", "호" => "ho", "후" => "hu", "햐" => "hya", "혜" => "hye", "효" => "hyo", "휘" => "hyu", 
                    "까" => "ja", "께" => "je", "끼" => "ji", "꼬" => "jo", "꾸" => "ju", "꺄" => "jya", "꼐" => "jye", "꾜" => "jyo", "뀌" => "jyu",
                    "카" => "ka", "케" => "ke", "키" => "ki", "코" => "ko", "쿠" => "ku", "캬" => "kya", "켸" => "kye", "쿄" => "kyo", "퀴" => "kyu",
                    "라" => "la", "레" => "le", "리" => "li", "로" => "lo", "루" => "lu", "랴" => "lya", "례" => "lye", "료" => "lyo", "뤼" => "lyu",
                    "마" => "ma", "메" => "me", "미" => "mi", "모" => "mo", "무" => "mu", "먀" => "mya", "몌" => "mye", "묘" => "myo", "뮈" => "myu", 
                    "나" => "na", "네" => "ne", "니" => "ni", "노" => "no", "누" => "nu", "냐" => "nya", "녜" => "nye", "뇨" => "nyo", "뉘" => "nyu", 
                    "빠" => "pa", "뻬" => "pe", "삐" => "pi", "뽀" => "po", "뿌" => "pu", "뺘" => "pya", "뼤" => "pye", "뾰" => "pyo", "쀠" => "pyu", 
                    "사" => "sa", "세" => "se", "시" => "si", "소" => "so", "수" => "su", "샤" => "sya", "셰" => "sye", "쇼" => "syo", "쉬" => "syu",
                    "타" => "ta", "테" => "te", "티" => "ti", "토" => "to", "투" => "tu", "탸" => "tya", "톄" => "tye", "툐" => "tyo", "튀" => "tyu", 
                    "와" => "wa", "웨" => "we", "의" => "wi", "워" => "wo",
                    "싸" => "xa", "쎄" => "xe", "씨" => "xi", "쏘" => "xo", "쑤" => "xu", "쌰" => "xya", "쎼" => "xye", "쑈" => "xyo", "쒸" => "xyu",
                    "자" => "za", "제" => "ze", "지" => "zi", "조" => "zo", "주" => "zu", "쟈" => "zya", "졔" => "zye", "죠" => "zyo", "쥐" => "zyu",
                    "따" => "swa", "떼" => "swe", "띠" => "swi", "또" => "swo", 
                    "짜" => "tsa", "쩨" => "tse", "찌" => "tsi", "쪼" => "tso", "쭈" => "tsu", "쨔" => "tsya", "쪠" => "tsye", "쬬" => "tsyo", "쮜" => "tsyu", 
                    "차" => "txa", "체" => "txe", "치" => "txi", "초" => "txo", "추" => "txu", "챠" => "txya", "쳬" => "txye", "쵸" => "txyo", "취" => "txyu", 
                    "은" => "n", "읏" => "k"}
  HANGEUL_TABLE = {"a" => "아", "e" => "에", "i" => "이", "o" => "오", "u" => "우", "ya" => "야", "ye" => "예", "yo" => "요", "yu" => "위", 
                   "ba" => "바", "be" => "베", "bi" => "비", "bo" => "보", "bu" => "부", "bya" => "뱌", "bye" => "볘", "byo" => "뵤", "byu" => "뷔",
                   "da" => "다", "de" => "데", "di" => "디", "do" => "도", "du" => "두", "dya" => "댜", "dye" => "뎨", "dyo" => "됴", "dyu" => "뒤",
                   "fa" => "파", "fe" => "페", "fi" => "피", "fo" => "포", "fu" => "푸", "fya" => "퍄", "fye" => "폐", "fyo" => "표", "fyu" => "퓌",
                   "ga" => "가", "ge" => "게", "gi" => "기", "go" => "고", "gu" => "구", "gya" => "갸", "gye" => "계", "gyo" => "교", "gyu" => "귀",
                   "ha" => "하", "he" => "헤", "hi" => "히", "ho" => "호", "hu" => "후", "hya" => "햐", "hye" => "혜", "hyo" => "효", "hyu" => "휘",
                   "ja" => "까", "je" => "께", "ji" => "끼", "jo" => "꼬", "ju" => "꾸", "jya" => "꺄", "jye" => "꼐", "jyo" => "꾜", "jyu" => "뀌",
                   "ka" => "카", "ke" => "케", "ki" => "키", "ko" => "코", "ku" => "쿠", "kya" => "캬", "kye" => "켸", "kyo" => "쿄", "kyu" => "퀴",
                   "la" => "라", "le" => "레", "li" => "리", "lo" => "로", "lu" => "루", "lya" => "랴", "lye" => "례", "lyo" => "료", "lyu" => "뤼",
                   "ma" => "마", "me" => "메", "mi" => "미", "mo" => "모", "mu" => "무", "mya" => "먀", "mye" => "몌", "myo" => "묘", "myu" => "뮈",
                   "na" => "나", "ne" => "네", "ni" => "니", "no" => "노", "nu" => "누", "nya" => "냐", "nye" => "녜", "nyo" => "뇨", "nyu" => "뉘",
                   "pa" => "빠", "pe" => "뻬", "pi" => "삐", "po" => "뽀", "pu" => "뿌", "pya" => "뺘", "pye" => "뼤", "pyo" => "뾰", "pyu" => "쀠",
                   "sa" => "사", "se" => "세", "si" => "시", "so" => "소", "su" => "수", "sya" => "샤", "sye" => "셰", "syo" => "쇼", "syu" => "쉬", 
                   "ta" => "타", "te" => "테", "ti" => "티", "to" => "토", "tu" => "투", "tya" => "탸", "tye" => "톄", "tyo" => "툐", "tyu" => "튀", 
                   "wa" => "와", "we" => "웨", "wi" => "의", "wo" => "워",
                   "xa" => "싸", "xe" => "쎄", "xi" => "씨", "xo" => "쏘", "xu" => "쑤", "xya" => "쌰", "xye" => "쎼", "xyo" => "쑈", "xyu" => "쒸",
                   "za" => "자", "ze" => "제", "zi" => "지", "zo" => "조", "zu" => "주", "zya" => "쟈", "zye" => "졔", "zyo" => "죠", "zyu" => "쥐",
                   "swa" => "따", "swe" => "떼", "swi" => "띠", "swo" => "또",
                   "tsa" => "짜", "tse" => "쩨", "tsi" => "찌", "tso" => "쪼", "tsu" => "쭈", "tsya" => "쨔", "tsye" => "쪠", "tsyo" => "쬬", "tsyu" => "쮜",
                   "txa" => "차", "txe" => "체", "txi" => "치", "txo" => "초", "txu" => "추", "txya" => "챠", "txye" => "쳬", "txyo" => "쵸", "txyu" => "취",
                   "n" => "은", "k" => "읏"}

  def to_nagili_alphabet
    string = self.clone
    string = string.split("").map{|s| (ALPHABET_TABLE.key?(s)) ? ALPHABET_TABLE[s] : s}.join("")
    string.gsub!(/(a|e|i|o|u)b(a|e|i|o|u|yu)/){"#{$1}v#{$2}"}
    return string
  end

  def to_nagili_hangeul
    string = self.clone
    string.gsub!("v", "b")
    string.gsub!(/((b|d|f|g|h|j|k|l|m|n|p|s|t|w|x|z|sw|ts|tx|)y?(a|e|i|o|u))n(?!y?(a|e|i|o|u))/){(HANGEUL_TABLE.key?($1)) ? HANGEUL_TABLE[$1] + HANGEUL_TABLE["n"] : $1 + "n"}
    string.gsub!(/((b|d|f|g|h|j|k|l|m|n|p|s|t|w|x|z|sw|ts|tx|)y?(a|e|i|o|u))k(?!y?(a|e|i|o|u))/){(HANGEUL_TABLE.key?($1)) ? HANGEUL_TABLE[$1] + HANGEUL_TABLE["k"]: $1 + "k"}
    string.gsub!(/((b|d|f|g|h|j|k|l|m|n|p|s|t|w|x|z|sw|ts|tx|)y?(a|e|i|o|u))/){(HANGEUL_TABLE.key?($1)) ? HANGEUL_TABLE[$1] : $1}
   return string
  end

  def url_escape
    string = self.clone
    string.gsub!("%", "%25")
    string.gsub!("+", "%2B")
    string.gsub!("&", "%26")
    string.gsub!("=", "%3D")
    string.gsub!("?", "%3F")
    string.gsub!(" ", "+")
    return string
  end

  def html_escape
    string = self.clone
    string.gsub!("&", "&amp;")
    string.gsub!("<", "&lt;")
    string.gsub!(">", "&gt;")
    string.gsub!("\"", "&quot;")
    return string
  end

end