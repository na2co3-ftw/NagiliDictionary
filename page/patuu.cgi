#!/usr/bin/ruby
# coding: utf-8


$LOAD_PATH.unshift(File.dirname(__FILE__))
Dir.chdir(File.dirname(__FILE__))

require 'pp'
require 'nagili_material/utilities'
require 'nagili_material/word'
require 'nagili_material/mana'
require 'nagili_material/request'
require 'nagili_material/twitter'


class PatuuPanwan

  ADMINISTERS = [338352248, 4047551593, 126187393, 245768509, 219195704, 222024788]
  MAX_REACTIONS = 10
  HELP_DATA = ["「単語検索」を含んだツイートをリプライすると、かぎカッコ内の文字列を単語検索します。幻字表記, 京字表記, 京極表記のどれでも大丈夫です。",
               "「訳語検索」を含んだツイートをリプライすると、かぎカッコ内の文字列を訳語検索します。",
               "「造語依頼」を含んだツイートをリプライすると、かぎカッコ内の単語を造語依頼します。複数ある場合はコンマで区切ってください。",
               "「単語数」を含んだツイートをリプライすると、現在の凪霧辞典に登録されている単語の総数をリプライします。",
               "「最近の造語依頼」を含んだツイートをリプライすると、直近5件の造語依頼と造語依頼の総件数をリプライします。",
               "「CSV」を含んだツイートをリプライすると、凪霧辞典のCSVデータのURLをリプライします。"]

  def initialize
    @patuu = Twitter.new(:patuu)
    @nagili_bot = Twitter.new(:nagili_bot)
    @time = Time.now
    @output = ""
    @queue = []
    @count = 0
    @status = ""
  end

  def run
    print_html_header
    prepare
    begin
      if self.alive?    
        get_queue 
        arrange_queue
        tweet_word 
        arrange_backups 
        delete_logs
        react_mentions
        observe_sleep
        observe_wake
        observe_absent
        save_queue
        print_output
      end
    rescue => exception
      error(exception.message + "\n" + exception.backtrace.join("\n"))
    end
  end

  def react_mentions
    last_tweet_id = File.read("nagili/last_tweet_id.txt").to_i
    mentions = @patuu.mentions
    @output << "last_tweet_id: #{last_tweet_id}\n\n"
    unless mentions.include?("errors")
      mentions = mentions.select{|s| s["id"] > last_tweet_id}.sort_by{|s| s["id"]}[0...MAX_REACTIONS]
      if !mentions.empty? && self.awake?
        File.open("nagili/last_tweet_id.txt", "w") do |file|
          file.print(mentions[-1]["id"])
        end
      end
      mentions.each do |data|
        tweet_id = data["id"]
        reply = data["text"].pack_unicode
        reply = reply.gsub("&lt;", "<").gsub("&gt;", ">").gsub("&amp;", "&")
        reply_user_name = data["user"]["screen_name"]
        reply_user_id = data["user"]["id"]
        reply_tweet_id = data["in_reply_to_status_id"]
        conduct_option = [reply, reply_user_name, reply_user_id, reply_tweet_id, tweet_id]
        if self.awake?
          if !reply_tweet_id || !conduct_reply(*conduct_option)
            conduct(*conduct_option)
          end
        else
          conduct_sleeping(*conduct_option)
        end
        @count += 1
      end
    else
      @output << "＊ QUEUE ERROR\n"
      @output << mentions["errors"].pretty_inspect + "\n\n"
    end
  end

  def conduct_reply(reply, reply_user_name, reply_user_id, reply_tweet_id, tweet_id)
    result = @queue.reject! do |line|
      first_tweet_id, date, mode, options = line.strip.split(/;\s*/)
      mode = mode.intern
      options = options.split(/,\s*/)
      if reply_tweet_id == first_tweet_id.to_i
        if mode == :modify_word
          if reply.strip.match(/続く$/)
            previous_tweet_ids = options[2..-1] + [tweet_id.to_s]
            add_queue(tweet_id, :modify_word, options[0], options[1], previous_tweet_ids.join(", "))
          else
            additions = options[2..-1].map do |additional_tweet_id|
              additional_data = @patuu.tweet_by_id(additional_tweet_id.to_i)
              next (additional_data.include?("text")) ? additional_data["text"].pack_unicode.strip.gsub(/続く$/, "") : ""
            end
            modify_word(reply_user_name, tweet_id, options[0], options[1].intern, additions.join("") + reply)
          end
        elsif mode == :create_word
          if reply.strip.match(/続く$/)
            previous_tweet_ids = options[1..-1] + [tweet_id.to_s]
            add_queue(tweet_id, :create_word, options[0], previous_tweet_ids.join(", "))
          else
            additions = options[1..-1].map do |additional_tweet_id|
              additional_data = @patuu.tweet_by_id(additional_tweet_id.to_i)
              next (additional_data.include?("text")) ? additional_data["text"].pack_unicode.strip.gsub(/続く$/, "") : ""
            end
            create_word(reply_user_name, tweet_id, options[0], additions.join("") + reply)
          end
        elsif mode == :search_detailed_name && ["詳細", "詳しく"].any?{|s| reply.include?(s)}
          match = reply.match(/(\d+)/)
          detailed_index = (match) ? [match[1].to_i - 1, 0].max : 0
          search_name(reply_user_name, tweet_id, options[0], detailed_index)
        elsif mode == :add_requests && ["はい", "うん", "する", "します", "しといて", "よろしく", "お願い"].any?{|s| reply.include?(s)}
          add_requests(reply_user_name, tweet_id, options[0])
        elsif mode == :check_word_url && ["URL", "アドレス"].any?{|s| reply.include?(s)}
          check_word_url(reply_user_name, tweet_id, options[0])
        elsif mode == :check_multiple_word_url && ["URL", "アドレス"].any?{|s| reply.include?(s)}
          match = reply.match(/(\d+)/)
          index = (match) ? [[match[1].to_i - 1, 0].max, options.size - 1].min : 0
          check_word_url(reply_user_name, tweet_id, options[index])
        else
          next false
        end
        next true
      end
    end
    return result
  end

  def conduct(reply, reply_user_name, reply_user_id, reply_tweet_id, tweet_id)
    if reply.include?("訳語検索")
      search = reply.match(/「(.+)」/).to_a[1]
      search_meaning(reply_user_name, tweet_id, search)
    elsif reply.include?("単語検索")
      search = reply.match(/「(.+)」/).to_a[1]
      detailed_index = (["詳細", "詳しく"].any?{|s| reply.gsub(/「(.+)」/, "").include?(s)}) ? 0 : nil
      search_name(reply_user_name, tweet_id, search, detailed_index)
    elsif reply.include?("ランダム") && reply.include?("依頼")
      check_recent_requests(reply_user_name, tweet_id, true)
    elsif reply.include?("最近") && reply.include?("依頼")
      check_recent_requests(reply_user_name, tweet_id, false)
    elsif reply.include?("削除") && reply.include?("依頼")
      requests = reply.match(/「(.+)」/).to_a[1]
      delete_requests(reply_user_name, reply_user_id, tweet_id, requests)
    elsif reply.include?("依頼")
      requests = reply.match(/「(.+)」/).to_a[1]
      add_requests(reply_user_name, tweet_id, requests)
    elsif reply.include?("修正") || reply.include?("編集")
      data = {"訳語" => :meaning, "関連語" => :synonym, "語源" => :ethymology, "京極" => :raw_mana, "語法" => :usage, "用例" => :example}
      name = reply.match(/「(.+)」/).to_a[1]
      type = data.find{|s, _| reply.gsub(/「(.+)」/, "").include?(s)}.to_a[1]
      prepare_modify_word(reply_user_name, reply_user_id, tweet_id, name, type)
    elsif reply.include?("造語") || reply.include?("作成")
      name = reply.match(/「(.+)」/).to_a[1]
      prepare_create_word(reply_user_name, reply_user_id, tweet_id, name)
    elsif reply.include?("削除")
      name = reply.match(/「(.+)」/).to_a[1]
      delete_word(reply_user_name, reply_user_id, tweet_id, name)
    elsif reply.include?("更新")
      update_data(reply_user_name, reply_user_id, tweet_id)
    elsif reply.include?("単語数")
      check_word_number(reply_user_name, tweet_id)
    elsif reply.include?("CSV")
      check_csv_url(reply_user_name, tweet_id)
    elsif reply.include?("バージョン")
      check_version(reply_user_name, tweet_id)
    elsif reply.include?("緊急停止")
      force_halt(reply_user_name, reply_user_id, tweet_id)
    elsif reply.include?("できる") && ["?", "？"].any?{|s| reply.include?(s)} && ["何", "なに", "どう", "どんな"].any?{|s| reply.include?(s)}
      help(reply_user_name, tweet_id)
    elsif ["起きて", "起床"].any?{|s| reply.include?(s)}
    else
      favorite(tweet_id)
    end
  end

  def conduct_sleeping(reply, reply_user_name, reply_user_id, reply_tweet_id, tweet_id)
    if ["起きて", "起床"].any?{|s| reply.include?(s)}
      force_wake(reply_user_name, tweet_id)
    end
  end

  def search_name(user_name, tweet_id, search, detailed_index = nil)
    @output << "＊ SEARCH NAME\n"
    @output << "from: (#{user_name}, #{tweet_id}, #{search}, #{detailed_index})\n"
    content = "@#{user_name} "
    if search
      dictionary = WordDictionary.new
      matched = dictionary.search(search, 0, 5)[0]
      unless matched.empty?
        if detailed_index
          detailed_index = [[detailed_index, 0].max, matched.size - 1].min
          address = "@#{user_name} "
          content = matched[detailed_index].meaning.gsub("\n", "")
          new_tweet_id = tweet_id
          splited_content = content.split(//)
          content_length = 140 - address.length
          result = []
          3.times do
            part_data = splited_content[0...content_length]
            splited_content = splited_content[content_length..-1] || []
            unless part_data.empty?
              result = @patuu.reply(address + part_data.join(""), new_tweet_id)
              if result.include?("id")
                new_tweet_id = result["id"]
                add_queue(new_tweet_id, :check_word_url, matched[detailed_index].name)
              end
            else
              break
            end
          end
        else
          new_matched = matched.map do |word|
            next word.meaning.split("\n")[0].split("、")[0].gsub("\n", "")
          end
          content << "「#{search}」の検索結果はこうなってます→ "
          content << new_matched.join(" / ")
          result = @patuu.reply(content, tweet_id)
          if result.include?("id")
            add_queue(result["id"], :check_word_url, matched[0].name)
            add_queue(result["id"], :search_detailed_name, search)
          end
        end
      else
        content << "「#{search}」は辞書に載ってないです。" + self.addition
        result = @patuu.reply(content, tweet_id)
      end
    else
      content << "検索したい単語を「」の中に入れてリプしてください。" + self.addition
      result = @patuu.reply(content, tweet_id)
    end
    output_final_result(result)
  end

  def search_meaning(user_name, tweet_id, search)
    @output << "＊ SEARCH MEANING\n"
    @output << "from: (#{user_name}, #{tweet_id}, #{search})\n"
    content = "@#{user_name} "
    if search
      dictionary = WordDictionary.new
      matched = dictionary.search(search, 1, 5)[0]
      unless matched.empty?
        new_matched = matched.map do |word|
          yula = word.name.to_hangeul
          hacm = (word.reading != "") ? word.reading : word.name
          mana = word.mana
          hacm += word.unique_name.match(/(\(\d+\))/).to_a.fetch(1, "")
          next "#{mana} (#{yula}, #{hacm})"
        end
        search_words = matched.map{|s| s.name}.join(", ")
        content << "「#{search}」で検索しました→ "
        content << new_matched.join(" / ")
        result = @patuu.reply(content, tweet_id)
        if result.include?("id")
          add_queue(result["id"], :check_multiple_word_url, search_words)
        end
      else
        content << "「#{search}」が訳語になってる単語はないみたいです。造語依頼しますか? " + self.addition
        result = @patuu.reply(content, tweet_id)
        if result.include?("id")
          @output << "ask request: (#{result["id"]}, #{search})\n"
          add_queue(result["id"], :add_requests, search)
        end
      end
    else
      content << "検索したい単語を「」の中に入れてリプしてください。" + self.addition
      result = @patuu.reply(content, tweet_id)
    end
    output_final_result(result)
  end

  def add_requests(user_name, tweet_id, requests)
    @output << "＊ ADD REQUESTS\n"
    @output << "from: (#{user_name}, #{tweet_id}, #{requests})\n"
    if requests
      content = "@#{user_name} 入れておきました。" + self.addition
      RequestManager.new.add_requests(requests.split(/(?:\s*\\\s*|\s*¥\s*)/))
    else
      content = "@#{user_name} 依頼する単語を「」の中に入れてリプください。複数あるときは \\ (バックスラッシュ)で区切ってください。" + self.addition
    end
    result = @patuu.reply(content, tweet_id)
    output_final_result(result)
  end

  def delete_requests(user_name, user_id, tweet_id, requests)
    @output << "＊ DELETE REQUESTS\n"
    @output << "from: (#{user_name}, #{tweet_id}, #{requests})\n"
    if ADMINISTERS.include?(user_id)
      if requests
        content = "@#{user_name} 削除しました。" + self.addition
        RequestManager.new.delete_requests_loosely(requests.split(/(?:\s*\\\s*|\s*¥\s*)/))
      else
        content = "@#{user_name} 削除したい依頼をを「」の中に入れてリプください。複数あるときは \\ (バックスラッシュ)で区切ってください。" + self.addition
      end
    else
      content = "@#{user_name} すみません、あなたには依頼削除の権利がないです。" + self.addition
    end
    result = @patuu.reply(content, tweet_id)
    output_final_result(result)
  end

  def update_data(user_name, user_id, tweet_id)
    @output << "＊ UPDATE INDEX\n"
    @output << "from: (#{user_name}, #{tweet_id})\n"
    if ADMINISTERS.include?(user_id)
      Utilities.create_dictionary_data
      Utilities.create_suggestable_names
      Utilities.create_mana_data
      content = "@#{user_name} 更新しました。" + self.addition
    else
      content = "@#{user_name} すみません、あなたには辞書データを更新する権利がないです。" + self.addition
    end
    result = @patuu.reply(content, tweet_id)
    output_final_result(result)
  end

  def prepare_modify_word(user_name, user_id, tweet_id, name, type)
    @output << "＊ PREPARE MODIFY WORD\n"
    @output << "from: (#{user_name}, #{tweet_id}, #{name}, #{type})\n"
    if ADMINISTERS.include?(user_id)
      if name
        dictionary = WordDictionary.new
        matched = (name.match(/^[a-z0-9\(\)]+$/)) ? dictionary.search_strictly(name) : dictionary.search(name, 0, 5)[0]
        unless matched.empty?
          if type
            present_data = matched[0].send(type).gsub("\n", "\\")
            address = "@#{user_name} "
            content = "どう修正しますか? "
            content << "現在のデータ: " + present_data
            new_tweet_id = tweet_id
            splited_content = content.split(//)
            content_length = 140 - address.length
            result = []
            3.times do
              part_data = splited_content[0...content_length]
              splited_content = splited_content[content_length..-1] || []
              unless part_data.empty?
                result = @patuu.reply(address + part_data.join(""), new_tweet_id)
                if result.include?("id")
                  @output << "accept: (#{result["id"]}, #{matched[0].unique_name})\n"
                  add_queue(result["id"], :modify_word, "#{matched[0].unique_name}, #{type}")
                end
              else
                break
              end
            end
          else
            content = "@#{user_name} 修正するとこを指定してください。" + self.addition
            result = @patuu.reply(content, tweet_id)
          end
        else
          content = "@#{user_name} 単語が辞書に載ってないです。調べ直してもっかいお願いします。" + self.addition
          result = @patuu.reply(content, tweet_id)
        end
      else
        content = "@#{user_name} 修正したい単語を「」に入れてください。" + self.addition
        result = @patuu.reply(content, tweet_id)
      end
    else
      content = "@#{user_name} すみません、あなたには単語修正の権利がないです。" + self.addition
      result = @patuu.reply(content, tweet_id)
    end
    output_final_result(result)
  end

  def modify_word(user_name, tweet_id, name, type, modification)
    @output << "＊ MODIFY WORD\n"
    @output << "from: (#{user_name}, #{tweet_id}, #{name}, #{type})\n"
    modification.gsub!(/\@[a-zA-Z0-9_]+\s*/, "")
    modification.gsub!("\n", "")
    @output << "modification content: #{modification.strip}\n"
    modification.gsub!(/\s*\\\s*/, "\n")
    modification.gsub!(/\s*¥\s*/, "\n")
    dictionary = WordDictionary.new
    word = dictionary.search_strictly(name)[0]
    word.send(type.to_s + "=", modification)
    word.update
    result = dictionary.modify_word(word)
    Utilities.delete_backups
    @output << "modification result: #{result.to_s}\n"
    content = "@#{user_name} 修正しました。" + self.addition
    result = @patuu.reply(content, tweet_id)
    output_final_result(result)   
  end

  def prepare_create_word(user_name, user_id, tweet_id, name)
    @output << "＊ PREPARE CREATE WORD\n"
    @output << "from: (#{user_name}, #{tweet_id}, #{name})\n"
    if ADMINISTERS.include?(user_id)
      if name
        dictionary = WordDictionary.new
        matched = dictionary.search_strictly(name)
        if matched.empty?
          content = "@#{user_name} 訳語以下の部分を書いてください。" + self.addition
          result = @patuu.reply(content, tweet_id)
          if result.include?("id")
            @output << "accept: (#{result["id"]}, #{name})\n"
            add_queue(result["id"], :create_word, name)
          end
        else
          content = "@#{user_name} この単語はもうあります。" + self.addition
          result = @patuu.reply(content, tweet_id)
        end
      else
        content = "@#{user_name} 造語する単語を「」で書いてください。" + self.addition
        result = @patuu.reply(content, tweet_id)
      end
    else
      content = "@#{user_name} すみませんが、あなたには新規造語の権利がないです。。" + self.addition
      result = @patuu.reply(content, tweet_id)
    end
    output_final_result(result)
  end

  def create_word(user_name, tweet_id, name, creation)
    @output << "＊ CREATE WORD\n"
    @output << "from: (#{user_name}, #{tweet_id}, #{name})\n"
    creation.gsub!(/\@[a-zA-Z0-9_]+\s*/, "")
    creation.gsub!("\n", "")
    @output << "creation content: #{creation.strip}\n"
    creation.gsub!(/\s*\\\s*/, "\n")
    creation.gsub!(/\s*¥\s*/, "\n")
    splitted_creation = creation.split(/(#{Utilities::EXAMPLE_TAGS.join("|")})/, 2)
    dictionary = WordDictionary.new
    word = Word.new(name, "", "", "", "", splitted_creation[0], splitted_creation[1].to_s)
    result = dictionary.add_word(word)
    Utilities.delete_backups
    Utilities.change_due_date
    @output << "creation result: #{result.to_s}\n"
    content = "@#{user_name} 追加しました。" + self.addition
    result = @patuu.reply(content, tweet_id)
    output_final_result(result)  
  end

  def delete_word(user_name, user_id, tweet_id, name)
    @output << "＊ DELETE WORD\n"
    @output << "from: (#{user_name}, #{tweet_id}, #{name})\n"    
    if ADMINISTERS.include?(user_id)
      if name
        dictionary = WordDictionary.new
        matched = dictionary.search_strictly(name)
        unless matched.empty?
          dictionary.delete_word_by_name(name)
          Utilities.delete_backups
          content = "@#{user_name} 削除しました。" + self.addition
          result = @patuu.reply(content, tweet_id)          
        else
          content = "@#{user_name} 単語が辞書に載ってないです。調べ直してもっかいお願いします。" + self.addition
          result = @patuu.reply(content, tweet_id)
        end
      else
        content = "@#{user_name} 削除したい単語を「」で書いてください。" + self.addition
        result = @patuu.reply(content, tweet_id)
      end
    else
      content = "@#{user_name} すみませんが、あなたには単語削除の権利がないです。" + self.addition
      result = @patuu.reply(content, tweet_id)
    end
    output_final_result(result)
  end

  def check_word_number(user_name, tweet_id)
    @output << "＊ CHECK WORD NUMBER\n"
    @output << "from: (#{user_name}, #{tweet_id})\n"
    number = WordDictionary.new.size
    content = "@#{user_name} 今の単語数は#{number}語です。" + self.addition
    result = @patuu.reply(content, tweet_id)
    output_final_result(result)   
  end

  def check_recent_requests(user_name, tweet_id, random = false)
    @output << "＊ CHECK RECENT REQUESTS\n"
    @output << "from: (#{user_name}, #{tweet_id}, #{random})\n"
    requests = RequestManager.new.requests
    last_index = [requests.size - 5, 0].max
    index = (random) ? rand(last_index) : last_index 
    recent_requests = requests[index, 5].map{|s| "「#{s}」"}
    if random
      content = "@#{user_name} 現在の依頼数は#{recent_requests.size}件です。#{recent_requests.join("")}などの依頼があります。" + self.addition
    else
      content = "@#{user_name} 現在の依頼数は#{recent_requests.size}件です。最近では#{recent_requests.join("")}が依頼されました。" + self.addition
    end
    result = @patuu.reply(content, tweet_id)
    output_final_result(result)  
  end

  def check_word_url(user_name, tweet_id, name)
    @output << "＊ CHECK WORD URL\n"
    @output << "from: (#{user_name}, #{tweet_id}, #{name})\n"
    if name
      content = "@#{user_name} リンクです。" + self.addition
      content << " http://nagili.minibird.jp/page/nagili.cgi?mode=search&search=#{name.url_escape}"
    else
      content = "@#{user_name} 検索したい単語を「」に入れて指定してください。" + self.addition
    end
    result = @patuu.reply(content, tweet_id)
    output_final_result(result)  
  end

  def check_csv_url(user_name, tweet_id)
    @output << "＊ CHECK CSV URL\n"
    @output << "from: (#{user_name}, #{tweet_id})\n"
    content = "@#{user_name} 最新のCSVです。UTF-8で保存されているので、適宜文字コードの変換をしてください。" + self.addition
    content << " http://nagili.minibird.jp/page/nagili/raw_word.csv"
    result = @patuu.reply(content, tweet_id)
    output_final_result(result)
  end

  def check_version(user_name, tweet_id)
    @output << "＊ CHECK VERSION\n"
    @output << "from: (#{user_name}, #{tweet_id})\n"
    content = "@#{user_name} バージョン＝#{Utilities.version}です。" + self.addition
    result = @patuu.reply(content, tweet_id)
    output_final_result(result)   
  end

  def help(user_name, tweet_id)
    @output << "＊ HELP\n"
    @output << "from: (#{user_name}, #{tweet_id})\n"
    help_data = HELP_DATA[rand(HELP_DATA.size)]
    content = "@#{user_name} #{help_data}" + self.addition
    result = @patuu.reply(content, tweet_id)
    output_final_result(result) 
  end

  def force_wake(user_name, tweet_id)
    @output << "＊ FORCE WAKE\n"
    @output << "from: (#{user_name}, #{tweet_id})\n"
    content = "@#{user_name} おはようございます。処理するのでちょっと待ってください。"
    due_time = @time + 1800
    time_string = due_time.strftime("%H:%M")
    result = @patuu.reply(content, tweet_id)
    change_status("awake temporarily #{time_string}")
    output_final_result(result) 
  end

  def force_halt(user_name, user_id, tweet_id)
    @output << "＊ FORCE HALT\n"
    @output << "from: (#{user_name}, #{tweet_id})\n"
    if ADMINISTERS.include?(user_id)
      @output << "done\n\n"
      File.open("nagili/heart.txt", "w") do |file|
        file.write("dead")
      end
      print_output
      exit
    else
      @output << "not permitted"
    end
  end

  def favorite(tweet_id)
    @output << "＊ FAVORITE\n"
    result = @patuu.favorite(tweet_id)
    output_final_result(result)  
  end

  def arrange_backups
    if @time.hour == 4 && @time.min == 10
      Utilities.arrange_backups
    end
  end

  def delete_logs
    if @time.hour == 3 && @time.min == 10
      Utilities.delete_logs
    end
  end

  def tweet_word
    if @time.min == 0 || @time.min == 20 || @time.min == 40
      @nagili_bot.tweet(WordDictionary.new.tweet_text)
    end
  end

  def observe_sleep
    due_time = @status.match(/(\d\d):(\d\d)/).to_a[0]
    if (self.awake? && !self.awake_temporarily?) || (self.awake_temporarily? && due_time && due_time <= @time.strftime("%H:%M"))
      if (@time.hour == 0 && rand(12 - @time.min / 5) == 0) || @time.hour.between?(1, 6)
        result = @patuu.tweet("おやすみなさい。" + self.addition)
        change_status("sleeping")
        @output << "＊ SLEEP\n"
        output_final_result(result)
      end
    end
  end

  def observe_wake
    if self.sleeping?
      if @time.hour == 7 && rand(12 - @time.min / 5) == 0
        result = @patuu.tweet("おはようございます。" + self.addition)
        change_status("awake")
        @output << "＊ WAKE\n"
        output_final_result(result)
      end
    end
    if self.awake_temporarily? && @time.hour >= 7
      change_status("awake")
    end
  end

  def observe_absent
    if @time.hour == 20 && @time.min == 40
      date_string = Time.now.strftime("%Y/%m/%d")
      due_date_string = File.read("nagili/due_date.txt")
      if due_date_string <= date_string
        @patuu.tweet("@ayukawamay 最近造語がないですよ。")
        Utilities.change_due_date
      end
    end
  end

  def output_final_result(result)
    if result.include?("id")
      @output << "done: #{result["id"]}\n\n"
    else
      @output << result.pretty_inspect.pack_unicode.strip + "\n\n"
    end
  end

  def get_queue
    @queue = File.read("nagili/queue.txt").split(/\n/)
    @count = File.read("nagili/count.txt").to_i
  end

  def arrange_queue
    due_time = Time.now - 172800
    date_string = due_time.strftime("%Y/%m/%d")
    @queue.delete_if{|s| s.strip.split(/;\s*/)[1] < date_string}
  end

  def add_queue(tweet_id, mode, *options)
    date_string = Time.now.strftime("%Y/%m/%d")
    @queue << "#{tweet_id}; #{date_string}; #{mode}; #{options.join(", ")}"
  end

  def save_queue
    File.open("nagili/queue.txt", "w") do |file|
      file.write(@queue.join("\n"))
    end
    File.open("nagili/count.txt", "w") do |file|
      file.write((@count % 15).to_s)
    end
  end

  def change_status(status)
    File.open("nagili/heart.txt", "w") do |file|
      file.write(status.to_s)
    end
  end

  def prepare
    time_string = @time.strftime("%Y/%m/%d %H:%M:%S")
    @status = File.read("nagili/heart.txt")
    @output << "【 PatuuPanwan (#{Utilities.version}) @ #{time_string} #{@status} 】\n"
  end

  def error(message)
    @output << message.strip + "\n\n"
    print_output
  end

  def print_html_header
    print("Content-Type: text/plain\n\n")
  end

  def print_output
    time_string = @time.strftime("%Y%m%d")
    File.open("nagili/log/patuu-#{time_string}.txt", "a") do |file|
      file.print(@output)
    end
  end

  def addition
    fixed_count = @count % 15
    return fixed_count.to_s(2).split(//).map{|s| ["‌", "‍"][s.to_i]}.join("")
  end

  def alive?
    return @status.include?("awake") || @status.include?("sleeping")
  end

  def awake?
    return @status.include?("awake")
  end

  def awake_temporarily?
    return @status.include?("awake temporarily")
  end

  def sleeping?
    return @status.include?("sleeping")
  end

end


if RUBY_VERSION >= "1.9.0"
  Encoding.default_external = "UTF-8"
else
  $KCODE = "U"
end

PatuuPanwan.new.run