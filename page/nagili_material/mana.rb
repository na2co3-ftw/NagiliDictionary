# coding: utf-8


class ManaDictionary

  def initialize
    @manas = []
    load
  end

  def load
    data = File.read("nagili/single_manas.txt")
    data.each_line do |line|
      if match = line.match(/^(.+):\s*(.+)/)
        @manas << Mana.new(match[1], match[2].split(","))
      end
    end
  end

  # 辞書データから京極を検索します。
  # 検索結果とサジェスト結果の 2 つのデータを格納した配列を返しますが、サジェスト結果を表す配列は必ず空になります。
  def search(search, type)
    matched = []
    @manas.each do |mana|
      if mana.matched?(search, type)
        matched << mana
      end
    end
    matched = matched.sort_by{|s| s.name}
    return [matched, []]
  end

end


class Mana

  attr_accessor :name
  attr_accessor :readings
  attr_accessor :special_readings
  attr_accessor :radical
  attr_accessor :stroke_count
  attr_accessor :code

  def initialize(name, readings)
    @name = name
    @readings = readings
    @special_readings = []
    @radical = ""
    @stroke_count = 0
    @code = 0
  end

  # 指定された検索方法でこの単語データがマッチする場合 true を返します。
  def matched?(search, type)
    alphabet_search = search.to_alphabet
    if type == 0
      if @name == alphabet_search
        return true
      end
    elsif type == 1
      if @readings.include?(search) || @special_readings.any?{|_, s| s == search}
        return true
      end
    end
    return false
  end

end