# coding: utf-8


class WordDictionary

  def initialize
    @words = []
    load
  end

  def load
    data = File.read("nagili/words.csv")
    splited_data = data.scan(/"(.*?)","(.*?)","(.*?)","(.*?)","(.*?)","(.*?)","(.*?)"\n/m)
    @words = splited_data.map{|s| Word.new(*s)}
  end

  # 辞書データを PDIC 用 CSV 形式でファイルに保存します。
  # 正常にデータの保存が終了した場合は、データのバイト数を返します。
  # 辞書データは自動的にバックアップが取られます。
  def save_raw
    output = "word,trans,exp,level,memory,modify,pron,filelink\n"
    @words.each do |word|
      name = word.unique_name.csv_escape
      translation = word.translation.csv_escape
      explanation = word.explanation.csv_escape
      output << "\"#{name}\",\"#{translation}\",\"#{explanation}\",0,0,0,\"\"\n"
    end
    Utilities.backup_word_data
    File.open("nagili/raw_words.csv", "w") do |file|
      file.write(output)
    end
    return output.length
  end

  # 辞書データをファイルに保存します。
  # 正常にデータの保存が終了した場合は、データのバイト数を返します。
  def save
    output = ""
    @words.each do |word|
      data = [word.unique_name, word.meaning, word.synonym, word.ethymology, word.raw_mana, word.usage, word.example]
      output << data.map{|s| "\"#{s.strip.csv_escape}\""}.join(",") + "\n"
    end
    File.open("nagili/words.csv", "w") do |file|
      file.write(output)
    end
    return output.length
  end

  # 辞書データから単語を検索します。
  # 検索結果とサジェスト結果の 2 つのデータを格納した配列を返します。
  def search(search, type, agree)
    matched = []
    suggested = []
    conjugation = Utilities.conjugation(search)
    suggestable_names = Utilities.suggestable_names
    @words.each do |word|
      if word.matched?(search, type, agree)
        matched << word
      end
      if suggestion_type = word.suggested?(search, conjugation, suggestable_names, type, agree)
        suggested << [word, suggestion_type]
      end
    end
    matched = matched.sort_by{|s| s.unique_name}
    suggested = suggested.sort_by{|s, _| s.unique_name}
    return [matched, suggested]
  end

  # 辞書データから単語を厳密に検索します。
  # 検索内容と単語名が完全に一致するもののみを格納した配列を返します。
  def search_strictly(search)
    @words.each do |word|
      if word.unique_name == search
        return [word] 
      end
    end
    return []
  end

  # 辞書データに新しい単語データを追加し、ファイルに保存します。
  # 正常にデータの保存が終了した場合は、データのバイト数を返します。
  # 指定された単語がすでに登録されている場合は、単語の新規登録をせずに nil を返します。
  def add_word(word)
    match = @words.find{|s| s.unique_name == word.unique_name}
    unless match
      @words << word
      return [self.save, self.save_raw]
    else
      return nil
    end
  end

  # 既存の単語データを修正し、ファイルに保存します。
  # 正常にデータの保存が終了した場合は、データのバイト数を返します。
  # 指定された単語が登録されていない場合は、何の操作もせずに nil を返します。
  def modify_word(word)
    index = nil
    @words.each_with_index do |each_word, i|
      if each_word.unique_name == word.unique_name
        index = i
        break
      end
    end
    if index
      @words[index] = word
      return [self.save, self.save_raw]
    else
      return nil
    end
  end

  # 辞書データから指定された単語名の単語データを削除し、ファイルに保存します。
  # 正常にデータの保存が終了した場合は、データのバイト数を返します。  
  # 指定された単語が登録されていない場合は、単語の削除をせずに nil を返します。
  def delete_word_by_name(name)
    index = nil
    @words.each_with_index do |each_word, i|
      if each_word.unique_name == name
        index = i
        break
      end
    end
    if index
      @words.delete_at(index)
      return [self.save, self.save_raw]
    else
      return nil
    end
  end

  def each(&block)
    @words.each do |word|
      block.call(word)
    end
  end

  # 辞典データからランダムに単語データを取り出し、Twitter で呟くためのテキストにして返します。
  # 自動的に 140 文字以下になるように調整されます。
  def tweet_text
    word = @words[rand(@words.size)]
    output = ""
    text = ""
    text << word.name + " ― "
    text << word.translation.scan(/^\s*(［.+］.+)$/).reject{|s| !Utilities::WORD_CLASSES.any?{|t, _| s[0].include?(t)}}.map{|s| s[0].gsub(/>\s*/, "> ")}.join(" / ")
    text = text.split(//)[0...117].join("")
    output << text
    output << " http://nagili.minibird.jp/page/nagili.cgi?mode=search&search=#{word.name.url_escape}&type=0&agree=0"
    return output
  end

  def size
    return @words.size
  end

end


class Word

  attr_accessor :name
  attr_accessor :unique_name
  attr_accessor :meaning
  attr_accessor :synonym
  attr_accessor :ethymology
  attr_accessor :mana
  attr_accessor :reading
  attr_accessor :raw_mana
  attr_accessor :usage
  attr_accessor :example
  attr_accessor :translation
  attr_accessor :explanation

  def initialize(name, meaning, synonym, ethymology, mana, usage, example)
    @name = ""
    @unique_name = name
    @meaning = meaning
    @synonym = synonym
    @ethymology = ethymology
    @mana = ""
    @reading = ""
    @raw_mana = mana
    @usage = usage
    @example = example
    @translation = ""
    @explanation = ""
    update
  end

  def update
    if match = @raw_mana.match(/^([a-z\s\[\]\/]*)\s*([^a-z\s\[\]\/]+)/)
      @mana = match[2]
      @reading = match[1]
    end
    @name = @unique_name.gsub(/\s*\(\d+\)/, "")
    @translation = [@meaning, @synonym, @ethymology, @raw_mana, @usage].join("\n").gsub(/\n+/, "\n").strip
    @explanation = @example.strip
  end

  # 指定された検索方法でこの単語データがマッチする場合 true を返します。
  def matched?(search, type, agree)
    alphabet_search = search.to_alphabet
    hangeul_search = search.to_hangeul
    if type == 0
      if agree == 0 || agree == 5
        if @name == alphabet_search || @mana == hangeul_search
          return true
        end
      elsif agree == 1
        if @name =~ /#{alphabet_search}/ || @mana =~ /#{hangeul_search}/
          return true
        end
      end
    elsif type == 1
      if agree == 0 || agree == 5
        @meaning.each_line do |line|
          if line.gsub(/［(.+)］/, "").gsub(/<(.+)>/, "").split("、").map{|s| s.strip}.any?{|s| s == search}
            return true
          end
        end
      elsif agree == 1
        @meaning.each_line do |line|
          if line.gsub(/［(.+)］/, "").gsub(/<(.+)>/, "").split("、").map{|s| s.strip}.any?{|s| s =~ /#{search}/}
            return true
          end
        end
      end
    elsif type == 3
      all_data = [@unique_name, @meaning, @synonym, @ethymology, @raw_mana, @usage, @example]
      if all_data.join("\n") =~ /#{search}/
        return true
      end
    end
    return false
  end

  # 指定された検索方法でこの単語データがサジェストされる場合、サジェストの内容を返します。
  # サジェストされない場合は nil を返します。
  def suggested?(search, conjugation, suggestable_names, type, agree)
    alphabet_search = search.to_alphabet
    if type == 0 && agree == 0
      if @name.match(/lu$/) && Utilities::CONJUGATIVE_CLASSES.any?{|s| @meaning.include?(s)}
        conjugation.each do |original_search, conjugation_type|
          if @name == original_search
            return conjugation_type
          end
        end
      end
      if @name =~ /\s/
        @name.split(/\s/).each do |element|
          if element == alphabet_search && suggestable_names.include?(element)
            return "一部"
          end
        end
      end
    end
    return nil
  end

end


class << Word

  def new_raw(name, translation, explanation)
    meaning = ""
    synonym = ""
    ethymology = ""
    mana = ""
    usage = ""
    example = ""
    mana_flag = true
    ethymology_flag = true
    example_flag = false
    data = translation + "\n" + explanation
    data.each_line do |line|
      if Utilities::WORD_CLASSES.any?{|s, _| line.include?(s)}
        meaning << line
      elsif Utilities::WORD_TAGS.any?{|s| line.include?(s)}
        synonym << line
      elsif Utilities::MAIN_TAGS.any?{|s| line.include?(s)}
        usage << line
        example_flag = false
      elsif Utilities::EXAMPLE_TAGS.any?{|s| line.include?(s)}
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
    return Word.new(name, meaning, synonym, ethymology, mana, usage, example)
  end

end