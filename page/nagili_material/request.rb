# coding: utf-8


class RequestManager

  attr_reader :requests

  def initialize
    @requests = []
    load
  end

  def load
    @requests = File.read("nagili/requests.txt").split(/\r*\n/).reject{|s| s.match(/^\s*$/)}
  end

  # 造語依頼データをファイルに書き込みます。
  # 引数 requests には造語依頼データを格納した配列を渡してください。 
  # 正常にデータの書き込みが終了した場合は、依頼件数を返します。
  def add_requests(requests)
    @requests << requests
    File.open("nagili/requests.txt", "w") do |file|
      file.write(@requests.join("\n"))
    end
    return requests.size
  end

  # 指定された造語依頼データをファイルから削除します。
  # 引数 requests には、依頼データのインデックスと依頼データの内容の 2 つからなる配列を格納した配列を渡してください。
  # 正常にデータの削除が終了した場合は、削除件数を返します。
  # インデックスと内容が一致していないなどの原因で削除を行わなかった場合は、nil を返します。
  def delete_requests(requests)
    requests = requests.sort_by{|s| s[0]}
    if requests.all?{|s, t| @requests[s] == t}
      requests.reverse_each do |number, _|
        @requests.delete_at(number)
      end
      File.open("nagili/requests.txt", "w") do |file|
        file.write(@requests.join("\n"))
      end
      return requests.size
    else
      return nil
    end
  end

  # インデックスの一致チェックを行わずに、指定された造語依頼データをファイルから削除します。
  # 引数 requests には、依頼データを格納した配列を渡してください。
  # 正常にデータの削除が終了した場合は、削除件数を返します。
  def delete_requests_loosely(requests)
    requests = self.requests_data
    requests.each do |delete|
      @requests.delete(delete)
    end
    File.open("nagili/requests.txt", "w") do |file|
      file.write(@requests.join("\n"))
    end
    return requests.size
  end

end