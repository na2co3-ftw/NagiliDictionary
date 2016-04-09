#!/usr/bin/ruby
# coding: utf-8


require 'pp'
require 'material/nagili_utilities'
require 'material/twitter'


class PatuuPanwan

  ADMINISTERS = [338352248, 4047551593, 126187393, 245768509, 219195704, 222024788]
  MAX_REACTIONS = 10
  MAX_DICTIONARY_BACKUPS = 15
  MAX_PATUU_LOGS = 30
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
        tweet_random_word 
        arrange_dictionary_backups 
        arrange_patuu_logs
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
    last_tweet_id = File.read("nagili/last_tweet_id.txt", "r").to_i
    mentions = @patuu.mentions
    @output << "last_tweed_id: #{last_tweet_id}\n\n"
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
        reply.gsub!("&amp;", "&")
        reply.gsub!("&lt;", "<")
        reply.gsub!("&gt;", ">")
        reply_user_name = data["user"]["screen_name"]
        reply_user_id = data["user"]["id"]
        reply_tweet_id = data["in_reply_to_status_id"]
        queue_id = nil
        if self.awake?
          if reply_tweet_id
            @queue.each_with_index do |line, i|
              first_tweet_id, date, mode, options = line.strip.split(/;\s*/)
              mode = mode.intern
              options = options.split(/,\s*/)
              if reply_tweet_id == first_tweet_id.to_i
                if mode == :modify_word
                  if reply.strip.match(/続く$/)
                    previous_tweet_ids = options[2..-1] + [tweet_id.to_s]
                    add_queue(tweet_id, :modify_word, "#{options[0]}, #{options[1]}, #{previous_tweet_ids.join(", ")}")
                  else
                    additions = options[2..-1].map do |additional_tweet_id|
                      additional_data = @patuu.tweet_by_id(additional_tweet_id.to_i)
                      next (additional_data.include?("text")) ? additional_data["text"].pack_unicode.strip.gsub(/続く$/, "") : ""
                    end
                    modify_word(reply_user_name, tweet_id, options[0], options[1].intern, additions.join("") + reply)
                  end
                  queue_id = i
                  break
                elsif mode == :create_word
                  if reply.strip.match(/続く$/)
                    previous_tweet_ids = options[1..-1] + [tweet_id.to_s]
                    add_queue(tweet_id, :create_word, "#{options[0]}, #{previous_tweet_ids.join(", ")}")
                  else
                    additions = options[1..-1].map do |additional_tweet_id|
                      additional_data = @patuu.tweet_by_id(additional_tweet_id.to_i)
                      next (additional_data.include?("text")) ? additional_data["text"].pack_unicode.strip.gsub(/続く$/, "") : ""
                    end
                    create_word(reply_user_name, tweet_id, options[0], additions.join("") + reply)
                  end
                  queue_id = i
                  break
                elsif mode == :search_detailed_word && ["詳細", "詳しく"].any?{|s| reply.include?(s)}
                  match = reply.match(/(\d+)/)
                  detailed_index = (match) ? match[1].to_i - 1 : 0
                  detailed_index = [detailed_index, 0].max
                  search_word(reply_user_name, tweet_id, options[0], detailed_index)
                  queue_id = i
                  break
                elsif mode == :add_requests && ["はい", "うん", "する", "します", "しといて", "よろしく", "お願い"].any?{|s| reply.include?(s)}
                  add_requests(reply_user_name, tweet_id, options[0])
                  queue_id = i
                  break
                elsif mode == :check_word_url && ["URL", "アドレス"].any?{|s| reply.include?(s)}
                  check_word_url(reply_user_name, tweet_id, options[0])
                  queue_id = i
                  break
                elsif mode == :check_multiple_word_url && ["URL", "アドレス"].any?{|s| reply.include?(s)}
                  match = reply.match(/(\d+)/)
                  index = (match) ? match[1].to_i - 1 : 0
                  index = [[index, 0].max, options.size - 1].min
                  check_word_url(reply_user_name, tweet_id, options[index])
                  queue_id = i
                  break
                end
              end
            end
          end
          if queue_id
            @queue.delete_at(queue_id)
          else
            if reply.include?("訳語検索")
              match = reply.match(/「(.+)」/u) 
              word = (match) ? match[1] : nil
              search_meaning(reply_user_name, tweet_id, word)
            elsif reply.include?("単語検索")
              match = reply.match(/「(.+)」/u)
              word = (match) ? match[1] : nil
              fixed_reply = reply.gsub(/「(.+)」/, "")
              if ["詳細", "詳しく"].any?{|s| fixed_reply.include?(s)}
                search_word(reply_user_name, tweet_id, word, 0)
              else
                search_word(reply_user_name, tweet_id, word)
              end
            elsif reply.include?("ランダム") && reply.include?("依頼")
              check_recent_requests(reply_user_name, tweet_id, true)
            elsif reply.include?("最近") && reply.include?("依頼")
              check_recent_requests(reply_user_name, tweet_id, false)
            elsif reply.include?("削除") && reply.include?("依頼")
              match = reply.match(/「(.+)」/u)
              requests = (match) ? match[1] : nil
              delete_requests(reply_user_name, reply_user_id, tweet_id, requests)
            elsif reply.include?("依頼")
              match = reply.match(/「(.+)」/u)
              requests = (match) ? match[1] : nil
              add_requests(reply_user_name, tweet_id, requests)
            elsif reply.include?("修正") || reply.include?("編集")
              if match = reply.match(/「(.+)」/u)
                fixed_reply = reply.gsub(/「(.+)」/, "")
                if fixed_reply.include?("訳語")
                  modify_word_preparation(reply_user_name, reply_user_id, tweet_id, match[1], :meaning)
                elsif fixed_reply.include?("関連語")
                  modify_word_preparation(reply_user_name, reply_user_id, tweet_id, match[1], :synonym)
                elsif fixed_reply.include?("語源")
                  modify_word_preparation(reply_user_name, reply_user_id, tweet_id, match[1], :ethymology)
                elsif fixed_reply.include?("京極")
                  modify_word_preparation(reply_user_name, reply_user_id, tweet_id, match[1], :mana)
                elsif fixed_reply.include?("語法")
                  modify_word_preparation(reply_user_name, reply_user_id, tweet_id, match[1], :usage)
                elsif fixed_reply.include?("用例")
                  modify_word_preparation(reply_user_name, reply_user_id, tweet_id, match[1], :example)
                else 
                  modify_word_preparation(reply_user_name, reply_user_id, tweet_id, match[1], nil)
                end
              else
                modify_word_preparation(reply_user_name, reply_user_id, tweet_id, nil, nil)
              end
            elsif reply.include?("造語")
              if match = reply.match(/「(.+)」/u)
                create_word_preparation(reply_user_name, reply_user_id, tweet_id, match[1])
              else
                create_word_preparation(reply_user_name, reply_user_id, tweet_id, nil)
              end
            elsif reply.include?("削除")
              if match = reply.match(/「(.+)」/u)
                delete_word(reply_user_name, reply_user_id, tweet_id, match[1])
              else
                delete_word(reply_user_name, reply_user_id, tweet_id, nil)
              end              
            elsif reply.include?("単語数")
              check_word_number(reply_user_name, tweet_id)
            elsif reply.include?("CSV")
              check_csv_url(reply_user_name, tweet_id)
            elsif reply.include?("バージョン")
              check_version(reply_user_name, tweet_id)
            elsif reply.include?("緊急停止")
              force_halt(reply_user_name, reply_user_id, tweet_id)
            elsif reply.include?("できること") ||
                  (reply.include?("できる") && ["?", "？"].any?{|s| reply.include?(s)} && ["何", "なに", "どう", "どんな"].any?{|s| reply.include?(s)})
              help(reply_user_name, tweet_id)
            elsif ["起きて", "起床"].any?{|s| reply.include?(s)}
            else
              favorite(tweet_id)
            end
          end
        else
          if ["起きて", "起床"].any?{|s| reply.include?(s)}
            force_wake(reply_user_name, tweet_id)
          end
        end
        @count += 1
      end
    else
      @output << "＊ QUEUE ERROR\n"
      @output << mentions["errors"].pretty_inspect + "\n\n"
    end
  end

  def search_word(user_name, tweet_id, word, detailed_index = nil)
    @output << "＊ SEARCH WORD\n"
    @output << "from: (#{user_name}, #{tweet_id}, #{word}, #{detailed_index})\n"
    content = "@#{user_name} "
    if word
      matched = NagiliUtilities.search_word(word, 0, 5)[0]
      unless matched.empty?
        if detailed_index
          detailed_index = matched.size - 1 if detailed_index >= matched.size
          address = "@#{user_name} "
          content = matched[detailed_index][1].gsub("\n", "")
          address_length = address.length
          new_tweet_id = tweet_id
          splited_content = content.split(//u)
          content_length = 140 - address_length
          result = []
          3.times do
            part_data = splited_content[0...content_length]
            splited_content = (splited_content[content_length..-1]) ? splited_content[content_length..-1] : []
            unless part_data.empty?
              result = @patuu.reply(address + part_data.join(""), new_tweet_id)
              if result.include?("id")
                new_tweet_id = result["id"]
                add_queue(new_tweet_id, :check_word_url, matched[0][0].gsub(/\(\d+\)/, "").strip)
              end
            else
              break
            end
          end
        else
          search = matched.map do |search_data|
            next search_data[1].split("、")[0].gsub("\n", "")
          end
          content << "「#{word}」の検索結果はこうなってます→ "
          content << search.join(" / ")
          result = @patuu.reply(content, tweet_id)
          if result.include?("id")
            add_queue(result["id"], :check_word_url, matched[0][0].gsub(/\(\d+\)/, "").strip)
            add_queue(result["id"], :search_detailed_word, word)
          end
        end
      else
        content << "「#{word}」は辞書に載ってないです。" + self.addition
        result = @patuu.reply(content, tweet_id)
      end
    else
      content << "検索したい単語を「」の中に入れてリプしてください。" + self.addition
      result = @patuu.reply(content, tweet_id)
    end
    output_final_result(result)
  end

  def search_meaning(user_name, tweet_id, word)
    @output << "＊ SEARCH MEANING\n"
    @output << "from: (#{user_name}, #{tweet_id}, #{word})\n"
    content = "@#{user_name} "
    if word
      matched = NagiliUtilities.search_word(word, 1, 0)[0]
      unless matched.empty?
        search = matched.map do |search_data|
          yula = search_data[0].gsub(/\(\d+\)/, "").to_nagili_hangeul.strip
          match = search_data[4].match(/([a-z\s\[\]\/]*)\s*([^a-z\s\[\]\/]*)/)
          hacm = (match && match[1].strip != "") ? match[1].strip : search_data[0].gsub(/\(\d+\)/, "")
          mana = (match) ? match[2].strip : ""
          match_number = search_data[0].match(/(\(\d+\))/)
          hacm += (match_number) ? match_number[1] : ""
          next "#{mana} (#{yula}, #{hacm})"
        end
        search_words = matched.map{|s| s[0].gsub(/\(\d+\)/, "").strip}.join(", ")
        content << "「#{word}」で検索しました→ "
        content << search.join(" / ")
        result = @patuu.reply(content, tweet_id)
        add_queue(result["id"], :check_multiple_word_url, search_words) if result.include?("id")
      else
        content << "「#{word}」が訳語になってる単語はないみたいです。造語依頼しますか? " + self.addition
        result = @patuu.reply(content, tweet_id)
        if result.include?("id")
          @output << "ask request: (#{result["id"]}, #{word})\n"
          add_queue(result["id"], :add_requests, word) if result.include?("id")
        end
      end
    else
      content << "検索したい単語を「」の中に入れてリプしてください。" + self.addition
      result = @patuu.reply(content, tweet_id)
    end
    output_final_result(result)
  end

  def add_requests(user_name, tweet_id, requests)
    @output << "＊ REQUEST WORDS\n"
    @output << "from: (#{user_name}, #{tweet_id}, #{requests})\n"
    if requests
      content = "@#{user_name} 入れておきました。" + self.addition
      NagiliUtilities.add_requests(requests.split(/(?:\s*\\\s*|\s*¥\s*)/))
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
        NagiliUtilities.delete_requests_loosely(requests.split(/(?:\s*\\\s*|\s*¥\s*)/))
      else
        content = "@#{user_name} 削除したい依頼をを「」の中に入れてリプください。複数あるときは \\ (バックスラッシュ)で区切ってください。" + self.addition
      end
    else
      content = "@#{user_name} すみません、あなたには依頼削除の権利がないです。" + self.addition
    end
    result = @patuu.reply(content, tweet_id)
    output_final_result(result)
  end

  def modify_word_preparation(user_name, user_id, tweet_id, word, type)
    @output << "＊ MODIFY WORD PREPARATION\n"
    @output << "from: (#{user_name}, #{tweet_id}, #{word}, #{type})\n"
    if ADMINISTERS.include?(user_id)
      if word
        matched = (word.match(/^[a-z0-9\(\)]+$/)) ? NagiliUtilities.search_word_strictly(word) : NagiliUtilities.search_word(word, 0, 5)[0]
        unless matched.empty?
          if type
            type_index = {:meaning => 1, :synonym => 2, :ethymology => 3, :mana => 4, :usage => 5, :example => 6}[type]
            present_data = matched[0][type_index].gsub("\n", "\\")
            address = "@#{user_name} "
            content = "どう修正しますか? "
            content << "現在のデータ: " + present_data
            address_length = address.length
            new_tweet_id = tweet_id
            splited_content = content.split(//u)
            content_length = 140 - address_length
            result = []
            3.times do
              part_data = splited_content[0...content_length]
              splited_content = (splited_content[content_length..-1]) ? splited_content[content_length..-1] : []
              unless part_data.empty?
                result = @patuu.reply(address + part_data.join(""), new_tweet_id)
                if result.include?("id")
                  fixed_word = matched[0][0].strip
                  new_tweet_id = result["id"]
                  add_queue(new_tweet_id, :modify_word, "#{fixed_word}, #{type}")
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

  def modify_word(user_name, tweet_id, word, type, modification)
    @output << "＊ MODIFY WORD\n"
    @output << "from: (#{user_name}, #{tweet_id}, #{word}, #{type})\n"
    modification.gsub!(/\@[a-zA-Z0-9_]+\s*/, "")
    modification.gsub!("\n", "")
    @output << "modification content: #{modification.strip}\n"
    modification.gsub!(/\s*\\\s*/, "\n")
    modification.gsub!(/\s*¥\s*/, "\n")
    case type
    when :meaning
      result = NagiliUtilities.modify_fixed_dictionary_data(word, modification, nil, nil, nil, nil, nil)
    when :synonym
      result = NagiliUtilities.modify_fixed_dictionary_data(word, nil, modification, nil, nil, nil, nil)
    when :ethymology
      result = NagiliUtilities.modify_fixed_dictionary_data(word, nil, nil, modification, nil, nil, nil)
    when :mana
      result = NagiliUtilities.modify_fixed_dictionary_data(word, nil, nil, nil, modification, nil, nil)
    when :usage
      result = NagiliUtilities.modify_fixed_dictionary_data(word, nil, nil, nil, nil, modification, nil)
    when :example
      result = NagiliUtilities.modify_fixed_dictionary_data(word, nil, nil, nil, nil, nil, modification)
    end
    delete_dictionary_backups
    @output << "modification result: #{result.to_s}\n"
    content = "@#{user_name} 修正しました。" + self.addition
    result = @patuu.reply(content, tweet_id)
    output_final_result(result)   
  end

  def create_word_preparation(user_name, user_id, tweet_id, word)
    @output << "＊ CREATE WORD PREPARATION\n"
    @output << "from: (#{user_name}, #{tweet_id}, #{word})\n"
    if ADMINISTERS.include?(user_id)
      if word
        if NagiliUtilities.search_word_strictly(word).empty?
          content = "@#{user_name} 訳語以下の部分を書いてください。" + self.addition
          result = @patuu.reply(content, tweet_id)
          if result.include?("id")
            @output << "accept: (#{result["id"]}, #{word})\n"
            add_queue(result["id"], :create_word, word)
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

  def create_word(user_name, tweet_id, word, creation)
    @output << "＊ CREATE WORD\n"
    @output << "from: (#{user_name}, #{tweet_id}, #{word})\n"
    creation.gsub!(/\@[a-zA-Z0-9_]+\s*/, "")
    creation.gsub!("\n", "")
    @output << "creation content: #{creation.strip}\n"
    creation.gsub!(/\s*\\\s*/, "\n")
    creation.gsub!(/\s*¥\s*/, "\n")
    fixed_creation = creation.split(/(#{NagiliUtilities::EXAMPLE_TAGS.join("|")})/, 2)
    translation = fixed_creation[0]
    if fixed_creation.size > 1
      explanation = fixed_creation[1] + fixed_creation[2] 
    else
      explanation = ""
    end
    result = NagiliUtilities.add_dictionary_data(word, translation.strip, explanation.strip)
    delete_dictionary_backups
    @output << "creation result: #{result.to_s}\n"
    content = "@#{user_name} 追加しました。" + self.addition
    result = @patuu.reply(content, tweet_id)
    change_due_date
    output_final_result(result)  
  end

  def delete_word(user_name, user_id, tweet_id, word)
    @output << "＊ DELETE WORD\n"
    @output << "from: (#{user_name}, #{tweet_id}, #{word})\n"    
    if ADMINISTERS.include?(user_id)
      if word
        unless NagiliUtilities.search_word_strictly(word).empty?
          NagiliUtilities.delete_dictionary_data(word)
          delete_dictionary_backups
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
    number = NagiliUtilities.dictionary_data.size
    content = "@#{user_name} 今の単語数は#{number}語です。" + self.addition
    result = @patuu.reply(content, tweet_id)
    output_final_result(result)   
  end

  def check_recent_requests(user_name, tweet_id, random = false)
    @output << "＊ CHECK RECENT REQUESTS\n"
    @output << "from: (#{user_name}, #{tweet_id}, #{random})\n"
    data = NagiliUtilities.requests_data
    last_index = [data.size - 5, 0].max
    index = (random) ? rand(last_index) : last_index 
    recent_data = data[index, 5].map{|s| "「#{s}」"}
    if random
      content = "@#{user_name} 現在の依頼数は#{data.size}件です。#{recent_data.join("")}などの依頼があります。" + self.addition
    else
      content = "@#{user_name} 現在の依頼数は#{data.size}件です。最近では#{recent_data.join("")}が依頼されました。" + self.addition
    end
    result = @patuu.reply(content, tweet_id)
    output_final_result(result)  
  end

  def check_word_url(user_name, tweet_id, word)
    @output << "＊ CHECK WORD URL\n"
    @output << "from: (#{user_name}, #{tweet_id}, #{word})\n"
    if word
      content = "@#{user_name} リンクです。" + self.addition
      content << " http://nagili.minibird.jp/page/nagili.cgi?mode=search&search=#{word.url_escape}"
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
    content << " http://nagili.minibird.jp/page/nagili/dictionary.csv"
    result = @patuu.reply(content, tweet_id)
    output_final_result(result)
  end

  def check_version(user_name, tweet_id)
    @output << "＊ CHECK VERSION\n"
    @output << "from: (#{user_name}, #{tweet_id})\n"
    content = "@#{user_name} バージョン＝#{NagiliUtilities.version}です。" + self.addition
    result = @patuu.reply(content, tweet_id)
    output_final_result(result)   
  end

  def help(user_name, tweet_id)
    @output << "＊ HELP\n"
    @output << "from: (#{user_name}, #{tweet_id})\n"
    content = "@#{user_name} #{HELP_DATA[rand(6)]}" + self.addition
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
        file.print("dead")
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

  def arrange_dictionary_backups
    if @time.hour == 4 && @time.min == 10
      NagiliUtilities.backup_dictionary_data("regular")
      delete_dictionary_backups("regular")
    end
  end

  def delete_dictionary_backups(name = "temporary")
    entries = Dir.entries("nagili/backup/").select{|s| s.include?(name)}.sort
    deletion_size = [entries.size - MAX_DICTIONARY_BACKUPS, 0].max
    entries[0...deletion_size].each do |entry|
      File.delete("nagili/backup/" + entry)
    end
  end

  def arrange_patuu_logs
    if @time.hour == 3 && @time.min == 10
      entries = Dir.entries("nagili/log/").select{|s| s.include?("patuu")}.sort
      deletion_size = [entries.size - MAX_PATUU_LOGS, 0].max
      entries[0...deletion_size].each do |entry|
        File.delete("nagili/log/" + entry)
      end
    end
  end

  def tweet_random_word
    if @time.min == 0 || @time.min == 20 || @time.min == 40
      @nagili_bot.tweet(NagiliUtilities.random_tweet_text)
    end
  end

  def observe_sleep
    match = @status.match(/(\d\d):(\d\d)/)
    due_time = (match) ? match[0] : nil
    if (self.awake? && !self.awake_temporarily?) ||
       (self.awake_temporarily? && due_time && due_time <= @time.strftime("%H:%M"))
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
      due_date = ""
      File.open("nagili/due_date.txt", "r") do |file|
        due_date = file.read
      end
      if due_date <= date_string
        @patuu.tweet("@ayukawamay 最近造語がないですよ。")
        change_due_date
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
    File.open("nagili/queue.txt", "r") do |file|
      @queue = file.read.split(/\n/)
    end
    File.open("nagili/count.txt", "r") do |file|
      @count = file.read.to_i
    end
  end

  def arrange_queue
    due_time = Time.now - 172800
    date_string = due_time.strftime("%Y/%m/%d")
    @queue.delete_if{|s| s.strip.split(/;\s*/)[1] < date_string}
  end

  def add_queue(tweet_id, mode, options)
    date_string = Time.now.strftime("%Y/%m/%d")
    @queue << "#{tweet_id}; #{date_string}; #{mode}; #{options}"
  end

  def save_queue
    File.open("nagili/queue.txt", "w") do |file|
      file.print(@queue.join("\n"))
    end
    File.open("nagili/count.txt", "w") do |file|
      file.print((@count % 15).to_s)
    end
  end

  def change_status(status)
    File.open("nagili/heart.txt", "w") do |file|
      file.print(status)
    end
  end

  def change_due_date
    due_time = @time + 604800
    date_string = due_time.strftime("%Y/%m/%d")
    File.open("nagili/due_date.txt", "w") do |file|
      file.print(date_string)
    end
  end

  def prepare
    time_string = @time.strftime("%Y/%m/%d %H:%M:%S")
    File.open("nagili/heart.txt", "r") do |file|
      @status = file.read
    end
    @output << "【 PatuuPanwan (#{NagiliUtilities.version}) @ #{time_string} #{@status} 】\n"
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
$LOAD_PATH.unshift(File.dirname(__FILE__))
Dir.chdir(File.dirname(__FILE__))

PatuuPanwan.new.run