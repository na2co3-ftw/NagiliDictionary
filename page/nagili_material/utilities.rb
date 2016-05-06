# coding: utf-8


require 'nkf'


module Utilities;extend self

  WORD_CLASSES = {"［名詞］" => "noun", "［動詞］" => "verb", "［形容詞］" => "adjective", "［連体詞］" => "adjective", "［副詞］" => "adverb", "［感動詞］" => "interjection", "［接続詞］" => "conjunction",
                  "［助動詞］" => "verb", "［末動詞］" => "verb", "［接続助詞］" => "particle", "［等位接続詞］" => "conjunction", "［文頭接続詞］" => "conjunction",
                  "［終助詞］" => "particle", "［格助詞］" => "particle", "［副助詞］" => "particle", "［係助詞］" => "particle",
                  "［接尾辞］" => "suffix", "［接頭辞］" => "suffix", "［ユマナ］" => "noun", "［数詞］" => "noun", "［助数詞］" => "suffix"}
  SUGGESTABLE_CLASSES = ["［名詞］", "［動詞］", "［形容詞］", "［副詞］", "［助動詞］"]
  CONJUGATIVE_CLASSES = ["［動詞］", "［形容詞］", "［助動詞］"]
  MAIN_TAGS = ["［語法］", "［文化］", "［語義］"]
  WORD_TAGS = ["［類義語］", "［反意語］", "［対義語］", "［同義語］", "［一覧］"]
  EXAMPLE_TAGS = ["【用例】"]
  SUFFIXES = {"la" => "連用形", "li" => "名詞形", "le" => "命令形", "lo" => "仮定形", "lu" => "終止連体形", "lan" => "否定形", "lane" => "否定命令形", "lano" => "否定仮定形"}
  VOICES = {"" => "", "so" => "使役", "ju" => "受動", "an" => "丁寧", "mi" => "過去", "soju" => "使役受動", "soan" => "使役丁寧", "somi" => "使役過去", "juan" => "受動丁寧", "jumi" => "受動過去",
            "anmi" => "丁寧過去", "sojuan" => "使役受動丁寧", "sojumi" => "使役受動過去", "soanmi" => "使役丁寧過去", "juanmi" => "受動丁寧過去", "sojuanmi" => "使役受動丁寧過去"}
  MAX_BACKUPS = 15
  MAX_LOGS = 30

  # PDIC 用 CSV データからオンライン凪霧辞典で用いる辞書データを作成します。
  # 正常にデータの作成が終了した場合は、データのバイト数を返します。
  def create_word_data
    dictionary = File.read("nagili/raw_words.csv").scan(/"(.*?)","(.*?)","(.*?)",(.*?),(.*?),(.*?),"(.*?)"\n/m)
    output = ""
    dictionary.each do |data|
      name, translation, explanation, _ = data
      word = Word.new_raw(name, translation, explanation)
      data = [word.name, word.meaning, word.synonym, word.ethymology, word.mana, word.usage, word.example]
      output << data.map{|s| "\"#{s}\""}.join(",") + "\n"
    end
    File.open("nagili/words.csv", "w") do |file|
      file.write(output)
    end
    return output.length
  end

  # 辞書データから京極の情報を抜き出し、外部ファイルに保存します。
  def create_mana_data
    dictionary = WordDictionary.new
    manas = []
    single_manas = Hash.new{|h, k| h[k] = []}
    double_manas = Hash.new{|h, k| h[k] = []}
    unknown_manas = Hash.new{|h, k| h[k] = []}
    single_output = ""
    double_output = ""
    unknown_output = ""
    dictionary.each do |word|
      name = word.name.gsub(/\s/, "").strip
      unless name == "凡例"
        manas << [name, word.mana.to_alphabet]
      end
    end
    manas = manas.map do |name, mana|
      new_name, new_mana = name, mana
      if match = mana.match(/^([a-z]+)/)
        if name.match(/^#{match[1]}/)
          new_name = name.gsub(/^#{match[1]}/, "")
          new_mana = mana.gsub(/^#{match[1]}/, "")
        end
      end
      if match = mana.match(/([a-z]+)$/)
        if name.match(/#{match[1]}$/)
          new_name = name.gsub(/#{match[1]}$/, "")
          new_mana = mana.gsub(/#{match[1]}$/, "")
        end
      end
      next [new_name, new_mana]
    end
    manas.delete_if{|s, t| s.match(/^\s*$/) || t.match(/^\s*$/)}
    manas.each do |name, mana|
      if mana.split(//).size == 1
        single_manas[mana] << name
      end
    end
    manas.each do |name, mana|
      unknown_manas[mana] << name
    end
    single_manas.sort.each do |mana, names|
      names = names.map{|s| (s.include?(s + "n")) ? s + "n" : s}
      names.uniq!
      single_output << "#{mana}: #{names.join(",")}\n"
    end
    double_manas.sort.each do |mana, names|
      names.uniq!
      double_output << "#{mana}: #{names.join(",")}\n"
    end
    unknown_manas.sort.each do |mana, names|
      names.uniq!
      unknown_output << "#{mana}: #{names.join(",")}\n"
    end
    File.open("nagili/single_manas.txt", "w") do |file|
      file.write(single_output)
    end
    File.open("nagili/double_manas.txt", "w") do |file|
      file.write(double_output)
    end
    File.open("nagili/unknown_manas.txt", "w") do |file|
      file.write(unknown_output)
    end
  end

  def create_suggestable_names
    dictionary = WordDictionary.new
    data = []
    dictionary.each do |word|
      if !word.name.match(/\s/) && SUGGESTABLE_CLASSES.any?{|s| word.meaning.include?(s)}
        data << word.unique_name
      end
    end
    File.open("nagili/suggestables.txt", "w") do |file|
      file.write(data.join("\n"))
    end
  end

  # 辞書データを外部ファイルから読み込んでサーバー上に保存します。
  # データは自動的に文字コードを UTF-8 に変換して保存されます。
  # 正常にデータの保存が終了した場合は、データのバイト数を返します。
  def import_word_data(data)
    data = NKF.nkf("-w", data)
    Utilities.backup_word_data
    File.open("nagili/raw_words.csv", "w") do |file|
      file.write(data)
    end
    return data.length
  end

  # 辞書データのバックアップを取ります。
  # 正常にデータのバックアップが終了した場合は、データのバイト数を返します。
  def backup_word_data(name = "temporary")
    time_string = Time.now.strftime("%Y%m%d%H%M%S")
    old_data = File.read("nagili/raw_words.csv")
    File.open("nagili/backup/#{name}-#{time_string}.csv", "w") do |file|
      file.write(old_data)
    end
    return old_data.length
  end

  def arrange_backups
    Utilities.backup_word_data("regular")
    Utilities.delete_backups("regular")
  end

  def delete_backups(name = "temporary")
    entries = Dir.entries("nagili/backup/").select{|s| s.include?(name)}.sort
    deletion_size = [entries.size - MAX_BACKUPS, 0].max
    entries[0...deletion_size].each do |entry|
      File.delete("nagili/backup/" + entry)
    end
  end

  def delete_logs(name = "patuu")
    entries = Dir.entries("nagili/log/").select{|s| s.include?(name)}.sort
    deletion_size = [entries.size - MAX_LOGS, 0].max
    entries[0...deletion_size].each do |entry|
      File.delete("nagili/log/" + entry)
    end
  end

  def change_due_date
    due_time = Time.now + 604800
    date_string = due_time.strftime("%Y/%m/%d")
    File.open("nagili/due_date.txt", "w") do |file|
      file.print(date_string)
    end
  end

  def password
    return File.read("nagili/password.txt").strip
  end

  def version
    return File.read("nagili/version.txt").strip
  end

  def suggestable_names
    return File.read("nagili/suggestables.txt").split("\n")
  end

  def conjugation(search)
    conjugation = []
    alphabet_search = search.to_alphabet
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
    return conjugation
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

  def to_alphabet
    string = self.clone
    string = string.split("").map{|s| (ALPHABET_TABLE.key?(s)) ? ALPHABET_TABLE[s] : s}.join("")
    string.gsub!(/(a|e|i|o|u)b(a|e|i|o|u|yu)/){"#{$~[1]}v#{$~[2]}"}
    return string
  end

  def to_hangeul
    string = self.clone
    string.gsub!("v", "b")
    string.gsub!(/((b|d|f|g|h|j|k|l|m|n|p|s|t|w|x|z|sw|ts|tx|)y?(a|e|i|o|u))n(?!y?(a|e|i|o|u))/) do
      next (HANGEUL_TABLE.key?($~[1])) ? HANGEUL_TABLE[$~[1]] + HANGEUL_TABLE["n"] : $~[1] + "n"
    end
    string.gsub!(/((b|d|f|g|h|j|k|l|m|n|p|s|t|w|x|z|sw|ts|tx|)y?(a|e|i|o|u))k(?!y?(a|e|i|o|u))/) do
      next (HANGEUL_TABLE.key?($~[1])) ? HANGEUL_TABLE[$~[1]] + HANGEUL_TABLE["k"]: $~[1] + "k"
    end
    string.gsub!(/((b|d|f|g|h|j|k|l|m|n|p|s|t|w|x|z|sw|ts|tx|)y?(a|e|i|o|u))/) do
      next (HANGEUL_TABLE.key?($~[1])) ? HANGEUL_TABLE[$~[1]] : $~[1]
    end
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

  def csv_escape
    string = self.clone
    string.gsub!("\"\"", "\"")
    string.gsub!("\"", "\"\"")
    return string
  end

end