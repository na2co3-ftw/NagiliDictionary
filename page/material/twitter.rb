# coding: utf-8


require 'library/oauth'
require 'nkf'


class Twitter;include OAuth

  attr_reader 'user'
  attr_reader 'oauth_data'

  def initialize(user)
    @user = user
    @consumer = nil
    @endpoint = nil
    @oauth_data = Hash.new{|h, s| h[s] = {}}
    load_oauth_data
  end

  def load_oauth_data
    type = :unknown
    File.open("nagili/oauth.txt") do |file|
      file.each_line do |line|
        if match = line.match(/^\*\s*([\w_]+)/)
          type = match[1].intern
        elsif match = line.match(/^\s*(.+)\s*,\s*(.+)/)
          @oauth_data[type][match[1].intern] = match[2]
        end
      end
    end
    @consumer = Consumer.new(@oauth_data[:consumer_key][@user], @oauth_data[:consumer_secret][@user], {:site => "https://api.twitter.com/"})
    @endpoint = AccessToken.new(@consumer, @oauth_data[:access_token][@user], @oauth_data[:access_secret][@user])
  end

  def get(url)
    return @endpoint.get(url).body.to_ruby
  end

  def post(url, parameter)
    return @endpoint.post(url, parameter).body.to_ruby
  end

  def tweet_by_id(id)
    return self.get("https://api.twitter.com/1.1/statuses/show.json?id=#{id}")
  end

  def mentions(since_id = nil)
    unless since_id
      return self.get("https://api.twitter.com/1.1/statuses/mentions_timeline.json")
    else
      return self.get("https://api.twitter.com/1.1/statuses/mentions_timeline.json?since_id=#{since_id}")
    end
  end

  def tweet(content)
    return self.post("https://api.twitter.com/1.1/statuses/update.json", {:status => content})
  end

  def reply(content, to_id)
    return self.post("https://api.twitter.com/1.1/statuses/update.json", {:status => content, :in_reply_to_status_id => to_id})
  end

  def favorite(to_id)
    return self.post("https://api.twitter.com/1.1/favorites/create.json", {:id => to_id})
  end

end


class String

  def to_ruby
    string = self.clone
    string.gsub!("\":", "\"=>")
    string.gsub!("null,", "nil,")
    string.gsub!("null}", "nil}")
    return eval(string)
  end

  def pack_unicode
    string = self.clone
    return string.gsub(/u([0-9a-f]{4})/){[$1.to_i(16)].pack("U*")}
  end

end


