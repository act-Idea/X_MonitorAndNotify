document.addEventListener('DOMContentLoaded', function(){
  document.querySelectorAll('.toggle-checkbox').forEach(function(cb){
    cb.addEventListener('change', function(){
      var monitorId = cb.getAttribute('data-monitor-id');
      var isEnabled = cb.checked;
      fetch('/monitor/' + monitorId + '/toggle', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        credentials: 'same-origin',
        body: JSON.stringify({is_enabled: isEnabled})
      }).then(function(res){
        if (!res.ok) throw res;
        return res.json();
      }).then(function(data){
        if (!data.success) {
          cb.checked = !isEnabled;
          alert('更新に失敗しました: ' + (data.error || '不明なエラー'));
        }
      }).catch(function(){
        cb.checked = !isEnabled;
        alert('更新に失敗しました。');
      });
    });
  });
});
