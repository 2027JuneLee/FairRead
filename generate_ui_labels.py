import argparse
import json
from collections import OrderedDict
from pathlib import Path


TRANSLATIONS = [
    ("Home", "Inicio", "首页", "홈"),
    ("News", "Noticias", "新闻", "뉴스"),
    ("Debate", "Debate", "辩论", "토론"),
    ("Profile", "Perfil", "个人资料", "프로필"),
    ("Statistics", "Estadísticas", "统计", "통계"),
    ("Login", "Iniciar sesión", "登录", "로그인"),
    ("Logout", "Cerrar sesión", "登出", "로그아웃"),
    ("Bias Classification", "Clasificación de sesgo", "倾向分类", "편향 분류"),
    ("Summary", "Resumen", "摘要", "요약"),
    ("Keywords", "Palabras clave", "关键词", "키워드"),
    ("Reason", "Razón", "理由", "이유"),
    ("Username", "Nombre de usuario", "用户名", "사용자명"),
    ("Password", "Contraseña", "密码", "비밀번호"),
    ("Not a member?", "¿No tienes cuenta?", "还没有账号？", "아직 계정이 없으신가요?"),
    ("Sign up", "Regístrate", "注册", "회원가입"),
    ("Select your gender", "Selecciona tu género", "请选择性别", "성별을 선택하세요"),
    ("Select your birthday", "Selecciona tu fecha de nacimiento", "请选择生日", "생년월일을 선택하세요"),
    ("Male", "Masculino", "男性", "남성"),
    ("Female", "Femenino", "女性", "여성"),
    ("Other", "Otro", "其他", "기타"),
    ("Register", "Registrarse", "注册", "가입하기"),
    ("Registration complete", "Registro completado", "注册完成", "가입 완료"),
    ("Your account was created successfully. You can now sign in.", "Tu cuenta se creó correctamente. Ahora puedes iniciar sesión.", "您的账号已成功创建。现在可以登录。", "계정이 성공적으로 생성되었습니다. 이제 로그인하실 수 있습니다."),
    ("Go to Login", "Ir al inicio de sesión", "前往登录", "로그인으로 이동"),
    ("Already have an account?", "¿Ya tienes una cuenta?", "已经有账号？", "이미 계정이 있으신가요?"),
    ("Sign in", "Iniciar sesión", "登录", "로그인"),
    ("News Classifier", "Clasificador de noticias", "新闻分类器", "뉴스 분류기"),
    ("We will classify the news for you!", "¡Clasificaremos la noticia por ti!", "我们将为您分析新闻倾向！", "뉴스 성향을 분석해 드립니다!"),
    ("How to use", "Cómo usarlo", "使用方法", "사용 방법"),
    ("Attach File", "Adjuntar archivo", "附加文件", "파일 첨부"),
    ("Paste or type article text or notes here...", "Pega o escribe aquí el texto del artículo o tus notas...", "在此粘贴或输入文章正文或笔记...", "기사 본문이나 메모를 여기에 붙여넣거나 입력하세요..."),
    ("Bias Class:", "Clase de sesgo:", "倾向类别：", "편향 분류:"),
    ("Bias Scores:", "Puntuaciones de sesgo:", "倾向分数：", "편향 점수:"),
    ("Left:", "Izquierda:", "左翼：", "좌파:"),
    ("Center:", "Centro:", "中间：", "중도:"),
    ("Right:", "Derecha:", "右翼：", "우파:"),
    ("Not analyzed yet", "Aún no analizado", "尚未分析", "아직 분석되지 않았습니다"),
    ("Reason for Bias", "Motivo del sesgo", "倾向原因", "편향 이유"),
    ("Analysis pending...", "Análisis pendiente...", "分析中...", "분석 중..."),
    ("News Summary", "Resumen de la noticia", "新闻摘要", "뉴스 요약"),
    ("Summary will appear here...", "El resumen aparecerá aquí...", "摘要将显示在这里...", "요약이 여기에 표시됩니다..."),
    ("Keywords will be shown here...", "Las palabras clave se mostrarán aquí...", "关键词将显示在这里...", "키워드가 여기에 표시됩니다..."),
    ("How to use the News Classifier", "Cómo usar el clasificador de noticias", "如何使用新闻分类器", "뉴스 분류기 사용 방법"),
    ("Ways to submit", "Formas de envío", "提交方式", "제출 방법"),
    ("Paste text", "Pegar texto", "粘贴文本", "텍스트 붙여넣기"),
    ("Paste any article text or your notes, then press Enter or click the send icon.", "Pega el texto de cualquier artículo o tus notas y luego presiona Enter o haz clic en el icono de enviar.", "粘贴任意文章文本或您的笔记，然后按 Enter 键或点击发送图标。", "기사 본문이나 메모를 붙여넣은 뒤 Enter를 누르거나 보내기 아이콘을 클릭하세요."),
    ("Paste a link", "Pegar un enlace", "粘贴链接", "링크 붙여넣기"),
    ("Drop an article URL. We'll fetch its content when possible and analyze it.", "Introduce la URL de un artículo. Recuperaremos su contenido cuando sea posible y lo analizaremos.", "输入文章 URL。若可获取内容，我们会抓取并进行分析。", "기사 URL을 입력하세요. 가능하면 본문을 가져와 분석합니다."),
    ("Upload a file", "Subir un archivo", "上传文件", "파일 업로드"),
    ("PDF or DOCX supported. If a file is attached, it takes priority over typed text.", "Compatible con PDF o DOCX. Si adjuntas un archivo, tendrá prioridad sobre el texto escrito.", "支持 PDF 或 DOCX。如果附加了文件，将优先处理文件而非输入文本。", "PDF 또는 DOCX를 지원합니다. 파일이 첨부되면 입력한 텍스트보다 우선 처리됩니다."),
    ("What you'll see", "Lo que verás", "您将看到", "표시되는 정보"),
    ("Left / Center / Right Scores", "Puntuaciones de izquierda / centro / derecha", "左 / 中 / 右分数", "좌 / 중 / 우 점수"),
    ("Tips & limits", "Consejos y límites", "提示与限制", "안내 및 제한사항"),
    ("Filenames should be English letters/numbers only", "Los nombres de archivo deben usar solo letras y números en inglés", "文件名只能使用英文字母和数字", "파일 이름은 영문자와 숫자만 사용하세요"),
    ("For paywalled pages, paste the article text or upload a PDF.", "En páginas con muro de pago, pega el texto del artículo o sube un PDF.", "对于付费墙页面，请粘贴文章正文或上传 PDF。", "유료 구독이 필요한 페이지는 기사 본문을 붙여넣거나 PDF를 업로드해 주세요."),
    ("Very long documents can take longer to process.", "Los documentos muy largos pueden tardar más en procesarse.", "文档过长时，处理时间可能更长。", "매우 긴 문서는 처리 시간이 더 오래 걸릴 수 있습니다."),
    ("If content extraction fails, try another link or paste the text directly.", "Si falla la extracción del contenido, prueba con otro enlace o pega el texto directamente.", "如果内容提取失败，请尝试其他链接或直接粘贴文本。", "내용 추출에 실패하면 다른 링크를 시도하거나 본문을 직접 붙여넣어 주세요."),
    ("We analyze your input and show results on the right.", "Analizamos tu contenido y mostramos los resultados a la derecha.", "我们会分析您的输入，并在右侧显示结果。", "입력하신 내용을 분석한 뒤 결과를 오른쪽에 표시합니다."),
    ("Got it", "Entendido", "知道了", "확인했습니다"),
    ("Analyzing, please wait...", "Analizando, por favor espera...", "正在分析，请稍候...", "분석 중입니다. 잠시만 기다려 주세요..."),
    ("Please rename the file using only English letters, numbers, spaces, underscores, hyphens, and dots (e.g., news_article_2025.pdf).", "Cambia el nombre del archivo usando solo letras en inglés, números, espacios, guiones bajos, guiones y puntos (p. ej., news_article_2025.pdf).", "请将文件重命名为仅使用英文字母、数字、空格、下划线、连字符和点（例如：news_article_2025.pdf）。", "파일 이름은 영문자, 숫자, 공백, 밑줄, 하이픈, 마침표만 사용하여 다시 지정해 주세요(예: news_article_2025.pdf)."),
    ("Done Processing. Please check the right side.", "Procesamiento completado. Revisa el lado derecho.", "处理完成。请查看右侧结果。", "처리가 완료되었습니다. 오른쪽 결과를 확인해 주세요."),
    ("Please attach a file or enter a message.", "Adjunta un archivo o escribe un mensaje.", "请附加文件或输入消息。", "파일을 첨부하거나 메시지를 입력해 주세요."),
    ("Filename not allowed. Use only English letters, numbers, spaces, underscores, hyphens, and dots.", "Nombre de archivo no permitido. Usa solo letras en inglés, números, espacios, guiones bajos, guiones y puntos.", "文件名不符合要求。请仅使用英文字母、数字、空格、下划线、连字符和点。", "허용되지 않는 파일 이름입니다. 영문자, 숫자, 공백, 밑줄, 하이픈, 마침표만 사용해 주세요."),
    ("My Data", "Mis datos", "我的数据", "내 데이터"),
    ("No data yet", "Aún no hay datos", "暂无数据", "아직 데이터가 없습니다"),
    ("Classify your first article to see bias distribution and topics here.", "Clasifica tu primer artículo para ver aquí la distribución de sesgo y los temas.", "先分析您的第一篇文章，即可在此查看倾向分布和主题。", "첫 번째 기사를 분석하면 여기에서 편향 분포와 주제를 확인할 수 있습니다."),
    ("Start classifying", "Empezar a clasificar", "开始分析", "분석 시작"),
    ("Bias Distribution", "Distribución de sesgo", "倾向分布", "편향 분포"),
    ("Average across your submissions", "Promedio de tus envíos", "基于您提交内容的平均值", "제출물 평균"),
    ("Top Topics", "Temas principales", "热门主题", "주요 주제"),
    ("Most frequent keywords", "Palabras clave más frecuentes", "最常见关键词", "가장 자주 나온 키워드"),
    ("Recent Classifications", "Clasificaciones recientes", "最近分类", "최근 분류 결과"),
    ("Prev", "Anterior", "上一页", "이전"),
    ("Next", "Siguiente", "下一页", "다음"),
    ("No recent items", "No hay elementos recientes", "暂无近期记录", "최근 항목이 없습니다"),
    ("Your latest classifications will appear here after you analyze an article.", "Tus clasificaciones más recientes aparecerán aquí después de analizar un artículo.", "分析文章后，您最近的分类结果将显示在这里。", "기사를 분석하면 최근 분류 결과가 여기에 표시됩니다."),
    ("Analyze an article", "Analizar un artículo", "分析一篇文章", "기사 분석하기"),
    ("Class:", "Clase:", "类别：", "분류:"),
    ("Mentions", "Menciones", "提及次数", "언급 수"),
    ("Total Users", "Usuarios totales", "用户总数", "총 사용자 수"),
    ("Active Users (30d)", "Usuarios activos (30 d)", "近30天活跃用户", "최근 30일 활성 사용자"),
    ("Total News", "Total de noticias", "新闻总数", "총 뉴스 수"),
    ("Recent News (30d)", "Noticias recientes (30 d)", "近30天新闻", "최근 30일 뉴스"),
    ("Chatbot Usage (Last 7 Days)", "Uso del chatbot (últimos 7 días)", "最近7天聊天机器人使用情况", "최근 7일 챗봇 사용량"),
    ("Daily requests", "Solicitudes diarias", "每日请求数", "일일 요청 수"),
    ("Monthly Chatbot Usage", "Uso mensual del chatbot", "每月聊天机器人使用情况", "월별 챗봇 사용량"),
    ("By month", "Por mes", "按月", "월별"),
    ("User Growth", "Crecimiento de usuarios", "用户增长", "사용자 증가"),
    ("Accounts over time", "Cuentas a lo largo del tiempo", "账号增长趋势", "기간별 계정 수"),
    ("Top Keywords", "Palabras clave principales", "热门关键词", "상위 키워드"),
    ("Most frequent", "Más frecuentes", "最常见", "가장 빈번한 항목"),
    ("Daily User Sessions", "Sesiones diarias de usuarios", "每日用户会话", "일일 사용자 세션"),
    ("Last 7 days", "Últimos 7 días", "最近7天", "최근 7일"),
    ("Average Bias Scores", "Puntuaciones promedio de sesgo", "平均倾向分数", "평균 편향 점수"),
    ("All", "Todos", "全部", "전체"),
    ("Chatbot Usage", "Uso del chatbot", "聊天机器人使用情况", "챗봇 사용량"),
    ("Sessions", "Sesiones", "会话数", "세션"),
    ("Users", "Usuarios", "用户数", "사용자"),
    ("Created on", "Creado el", "创建于", "생성일"),
    ("Back to Debates", "Volver a Debates", "返回辩论列表", "토론 목록으로"),
    ("Create Post", "Crear publicación", "发布帖子", "게시글 작성"),
    ("Add Related News", "Agregar noticia relacionada", "添加相关文章", "관련 뉴스 추가"),
    ("Discussion", "Discusión", "讨论", "토론"),
    ("Delete", "Eliminar", "删除", "삭제"),
    ("Like", "Me gusta", "点赞", "좋아요"),
    ("Comments", "Comentarios", "评论", "댓글"),
    ("Write a comment…", "Escribe un comentario…", "写下评论…", "댓글을 작성하세요…"),
    ("No posts yet. Be the first to contribute to the discussion.", "Aún no hay publicaciones. Sé la primera persona en contribuir a la discusión.", "还没有帖子。成为第一个参与讨论的人吧。", "아직 게시글이 없습니다. 첫 번째로 토론에 참여해 보세요."),
    ("Related News", "Noticias relacionadas", "相关新闻", "관련 뉴스"),
    ("More", "Más", "更多", "더보기"),
    ("Open original article", "Abrir artículo original", "打开原文", "원문 기사 열기"),
    ("Bias & Scores", "Sesgo y puntuaciones", "倾向与分数", "편향 및 점수"),
    ("Classification:", "Clasificación:", "分类：", "분류:"),
    ("Cast your view on this article's bias to see the full breakdown.", "Comparte tu opinión sobre el sesgo de este artículo para ver el desglose completo.", "发表您对这篇文章倾向的看法，即可查看完整分解。", "이 기사 편향에 대한 의견을 남기면 전체 분석 결과를 볼 수 있습니다."),
    ("Read Full Article", "Leer artículo completo", "阅读全文", "기사 전체 읽기"),
    ("Close", "Cerrar", "关闭", "닫기"),
    ("What is your opinion about this article's bias?", "¿Cuál es tu opinión sobre el sesgo de este artículo?", "您如何看待这篇文章的倾向？", "이 기사 편향에 대해 어떻게 생각하시나요?"),
    ("No news articles have been added yet.", "Aún no se han agregado artículos de noticias.", "还未添加新闻文章。", "아직 추가된 뉴스 기사가 없습니다."),
    ("Delete this post? This cannot be undone.", "¿Eliminar esta publicación? Esta acción no se puede deshacer.", "删除此帖子？此操作无法撤销。", "이 게시글을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다."),
    ("Delete this news item? This cannot be undone.", "¿Eliminar esta noticia? Esta acción no se puede deshacer.", "删除这条新闻？此操作无法撤销。", "이 뉴스 항목을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다."),
    ("Debates", "Debates", "辩论", "토론"),
    ("Open:", "Abiertos:", "进行中：", "진행 중:"),
    ("Closed:", "Cerrados:", "已关闭：", "종료됨:"),
    ("e.g., Should social media platforms be regulated like utilities?", "p. ej., ¿Deben regularse las plataformas de redes sociales como servicios públicos?", "例如：社交媒体平台是否应像公用事业一样受到监管？", "예: 소셜 미디어 플랫폼을 공공요금 서비스처럼 규제해야 할까요?"),
    ("Create Debate", "Crear debate", "创建辩论", "토론 생성"),
    ("Filter topics...", "Filtrar temas...", "筛选主题...", "주제 필터..."),
    ("Newest", "Más recientes", "最新", "최신순"),
    ("Oldest", "Más antiguos", "最早", "오래된순"),
    ("A → Z", "A → Z", "A → Z", "A → Z"),
    ("Z → A", "Z → A", "Z → A", "Z → A"),
    ("Created:", "Creado:", "创建时间：", "생성일:"),
    ("View", "Ver", "查看", "보기"),
    ("Close Debate", "Cerrar debate", "关闭辩论", "토론 종료"),
    ("No open debates yet.", "Aún no hay debates abiertos.", "还没有进行中的辩论。", "진행 중인 토론이 아직 없습니다."),
    ("No closed debates yet.", "Aún no hay debates cerrados.", "还没有已关闭的辩论。", "종료된 토론이 아직 없습니다."),
    ("Debate Topic", "Tema del debate", "辩论主题", "토론 주제"),
    ("Share Your Thoughts", "Comparte tu opinión", "分享您的看法", "의견을 공유해 주세요"),
    ("Your Post", "Tu publicación", "您的帖子", "내 게시글"),
    ("Write a clear, constructive contribution to the debate…", "Escribe una contribución clara y constructiva al debate…", "写下清晰且建设性的讨论内容…", "명확하고 건설적인 의견을 작성해 주세요…"),
    ("Suggested length:", "Longitud sugerida:", "建议长度：", "권장 분량:"),
    ("50–500 words", "50–500 palabras", "50–500 个词", "50~500단어"),
    ("/2000", "/2000", "/2000", "/2000"),
    ("Please revise your post to remove disallowed terms and ensure it's on-topic.", "Revisa tu publicación para eliminar términos no permitidos y asegurarte de que sea relevante.", "请修改您的帖子，删除不允许的用语，并确保内容与主题相关。", "허용되지 않는 표현을 제거하고 주제에 맞도록 게시글을 수정해 주세요."),
    ("Back to Debate", "Volver al debate", "返回辩论", "토론으로 돌아가기"),
    ("Submit Post", "Publicar", "提交帖子", "게시글 등록"),
    ("Please add a bit more detail (at least ~10 words).", "Añade un poco más de detalle (al menos ~10 palabras).", "请补充更多细节（至少约 10 个词）。", "내용을 조금 더 보완해 주세요(최소 약 10단어)."),
    ("Please keep your post on-topic and respectful. Posts are visible to others.", "Mantén tu publicación centrada en el tema y con respeto. Otras personas pueden verla.", "请确保您的帖子切题且尊重他人。帖子对其他人可见。", "게시글은 주제에 맞고 예의를 지켜 작성해 주세요. 다른 사용자에게 공개됩니다."),
    ("Stay relevant to", "Mantente relevante para", "请围绕以下主题", "다음 주제와 관련되게 작성해 주세요"),
    ("Support claims with sources when possible.", "Respalda tus afirmaciones con fuentes cuando sea posible.", "如有可能，请用来源支持您的观点。", "가능하면 출처를 통해 주장을 뒷받침해 주세요."),
    ("Use civil language. Critique ideas, not people.", "Usa un lenguaje respetuoso. Critica ideas, no personas.", "请使用文明用语。批评观点，而非针对个人。", "정중한 표현을 사용해 주세요. 사람보다 의견을 비판하세요."),
    ("No hate speech, harassment, or calls for violence. Avoid slurs and personal data.", "No se permite discurso de odio, acoso ni llamados a la violencia. Evita insultos y datos personales.", "禁止仇恨言论、骚扰或鼓动暴力。请避免使用侮辱性词语和个人信息。", "혐오 발언, 괴롭힘, 폭력 선동은 허용되지 않습니다. 비하 표현과 개인정보는 피해주세요."),
    ("No unrelated spam or promotional content.", "No se permite spam no relacionado ni contenido promocional.", "禁止发布无关垃圾信息或推广内容。", "관련 없는 스팸이나 홍보성 콘텐츠는 허용되지 않습니다."),
    ("Add News Article", "Agregar artículo de noticias", "添加新闻文章", "뉴스 기사 추가"),
    ("Attach a credible source, summarize clearly, and keep it civil.", "Adjunta una fuente creíble, resume con claridad y mantén un tono respetuoso.", "请附上可信来源，清晰概述内容，并保持文明表达。", "신뢰할 수 있는 출처를 첨부하고, 명확하게 요약하며, 정중한 표현을 유지해 주세요."),
    ("We store title, link, summary & content to compute bias scores.", "Guardamos el título, el enlace, el resumen y el contenido para calcular las puntuaciones de sesgo.", "我们会存储标题、链接、摘要和内容，以计算倾向分数。", "편향 점수를 계산하기 위해 제목, 링크, 요약 및 내용을 저장합니다."),
    ("Article Title", "Título del artículo", "文章标题", "기사 제목"),
    ("Enter the article headline…", "Introduce el titular del artículo…", "输入文章标题…", "기사 제목을 입력하세요…"),
    ("Keep it faithful to the original headline.", "Mantén fidelidad al titular original.", "保持与原标题一致。", "원래 제목의 의미를 충실히 반영해 주세요."),
    ("Article Link", "Enlace del artículo", "文章链接", "기사 링크"),
    ("https://example.com/news/article", "https://example.com/news/article", "https://example.com/news/article", "https://example.com/news/article"),
    ("We'll try to pull the full text from the URL for you to review and edit.", "Intentaremos extraer el texto completo desde la URL para que puedas revisarlo y editarlo.", "我们会尝试从该 URL 提取全文，供您查看和编辑。", "URL에서 본문을 가져와 검토하고 수정할 수 있도록 시도합니다."),
    ("Extract Content", "Extraer contenido", "提取内容", "본문 추출"),
    ("Summarize the article in 2–3 sentences…", "Resume el artículo en 2–3 oraciones…", "请用 2–3 句话概述文章…", "기사를 2~3문장으로 요약해 주세요…"),
    ("Be neutral and concise; avoid personal opinions here.", "Sé neutral y conciso; evita opiniones personales aquí.", "请保持中立简洁；此处避免加入个人观点。", "중립적이고 간결하게 작성해 주세요. 이곳에는 개인 의견을 넣지 마세요."),
    ("News Content", "Contenido de la noticia", "新闻内容", "뉴스 본문"),
    ("Paste or edit the extracted article text…", "Pega o edita el texto extraído del artículo…", "粘贴或编辑提取出的文章文本…", "추출된 기사 본문을 붙여넣거나 수정하세요…"),
    ("Edit for clarity. Don't include unrelated or harmful content.", "Edita para mayor claridad. No incluyas contenido no relacionado o perjudicial.", "请为清晰度进行编辑。不要包含无关或有害内容。", "더 명확하게 다듬어 주세요. 관련 없거나 유해한 내용은 포함하지 마세요."),
    ("Guidelines", "Pautas", "指南", "가이드라인"),
    ("Stay on topic and cite credible sources.", "Mantente en el tema y cita fuentes creíbles.", "请围绕主题并引用可信来源。", "주제를 벗어나지 말고 신뢰할 수 있는 출처를 인용해 주세요."),
    ("No hate speech, harassment, or personal attacks.", "No se permite discurso de odio, acoso ni ataques personales.", "禁止仇恨言论、骚扰或人身攻击。", "혐오 발언, 괴롭힘, 인신공격은 허용되지 않습니다."),
    ("Report misclassified or suspicious sources to an admin.", "Informa a una persona administradora sobre fuentes mal clasificadas o sospechosas.", "如发现误分类或可疑来源，请向管理员报告。", "잘못 분류되었거나 의심스러운 출처는 관리자에게 신고해 주세요."),
    ("After submission, bias and stance will be computed automatically.", "Tras el envío, el sesgo y la postura se calcularán automáticamente.", "提交后，倾向和立场将自动计算。", "제출 후 편향과 입장이 자동으로 계산됩니다."),
    ("Submit News", "Enviar noticia", "提交新闻", "뉴스 등록"),
    ("Please paste a valid link first.", "Primero pega un enlace válido.", "请先粘贴有效链接。", "먼저 올바른 링크를 붙여넣어 주세요."),
    ("Extracting…", "Extrayendo…", "正在提取…", "추출 중…"),
    ("Error:", "Error:", "错误：", "오류:"),
    ("Failed to extract content.", "No se pudo extraer el contenido.", "内容提取失败。", "내용을 추출하지 못했습니다."),
    ("Request failed. Please check the link or try again later.", "La solicitud falló. Verifica el enlace o inténtalo de nuevo más tarde.", "请求失败。请检查链接或稍后重试。", "요청에 실패했습니다. 링크를 확인하거나 잠시 후 다시 시도해 주세요."),
    ("Bias • Summary • Transparency", "Sesgo • Resumen • Transparencia", "倾向 • 摘要 • 透明度", "편향 • 요약 • 투명성"),
    ("See the story behind the story.", "Ve la historia detrás de la historia.", "看见新闻背后的脉络。", "기사 뒤에 숨은 맥락까지 살펴보세요."),
    ("FairRead analyzes any article for political lean, explains why, and returns a concise summary you can trust.", "FairRead analiza cualquier artículo para detectar su inclinación política, explica por qué y devuelve un resumen conciso en el que puedes confiar.", "FairRead 可分析任意文章的政治倾向，解释原因，并返回值得信赖的简明摘要。", "FairRead는 모든 기사의 정치적 성향을 분석하고 그 이유를 설명하며, 신뢰할 수 있는 간결한 요약을 제공합니다."),
    ("Analyze an Article", "Analizar un artículo", "分析文章", "기사 분석하기"),
    ("Explore Features", "Explorar funciones", "探索功能", "기능 살펴보기"),
    ("Private by default • URL · Text · PDF", "Privado por defecto • URL · Texto · PDF", "默认私密 • URL · 文本 · PDF", "기본 비공개 • URL · 텍스트 · PDF"),
    ("Preview", "Vista previa", "预览", "미리보기"),
    ("Bias · Confidence · Key signals", "Sesgo · Confianza · Señales clave", "倾向 · 置信度 · 关键信号", "편향 · 신뢰도 · 핵심 신호"),
    ("About", "Acerca de", "关于", "소개"),
    ("FairRead explained", "FairRead explicado", "FairRead 介绍", "FairRead 소개"),
    ("FairRead is a lightweight tool for evaluating news articles with clarity and speed. Paste a link, text, or PDF and receive an objective read on where the piece leans.", "FairRead es una herramienta ligera para evaluar artículos de noticias con claridad y rapidez. Pega un enlace, texto o un PDF y obtén una lectura objetiva de la inclinación de la pieza.", "FairRead 是一款轻量工具，可快速清晰地评估新闻文章。粘贴链接、文本或 PDF，即可获得对文章倾向的客观判断。", "FairRead는 뉴스 기사를 빠르고 명확하게 평가할 수 있는 가벼운 도구입니다. 링크, 텍스트 또는 PDF를 붙여넣으면 해당 기사 성향에 대한 객관적인 분석을 받아볼 수 있습니다."),
    ("Results include a brief rationale so you can see the cues behind the call — not just the label. Your history stays private and helps you understand your own reading patterns over time.", "Los resultados incluyen una breve explicación para que puedas ver las señales detrás de la evaluación, no solo la etiqueta. Tu historial permanece privado y te ayuda a comprender tus propios patrones de lectura con el tiempo.", "结果包含简要说明，让您看到判断背后的线索，而不仅仅是标签。您的历史记录默认保持私密，并帮助您长期了解自己的阅读模式。", "결과에는 간단한 근거가 함께 제공되어 단순한 라벨이 아니라 판단의 단서를 확인할 수 있습니다. 기록은 기본적으로 비공개로 유지되며, 시간이 지나며 자신의 읽기 패턴을 이해하는 데 도움이 됩니다."),
    ("Bias classification with confidence", "Clasificación de sesgo con nivel de confianza", "带置信度的倾向分类", "신뢰도와 함께 제공되는 편향 분류"),
    ("Evidence-based rationale (framing, sources, wording)", "Justificación basada en evidencia (enfoque, fuentes, redacción)", "基于证据的说明（框架、来源、措辞）", "근거 기반 설명(프레이밍, 출처, 표현)"),
    ("Concise, source-aware summary", "Resumen conciso y consciente de las fuentes", "简洁且关注来源的摘要", "출처를 고려한 간결한 요약"),
    ("Personal analytics with privacy by default", "Analítica personal con privacidad por defecto", "默认私密的个人分析", "기본 비공개 개인 분석"),
    ("Capabilities", "Capacidades", "功能", "주요 기능"),
    ("A focused toolkit for reading news clearly", "Un conjunto de herramientas enfocado para leer noticias con claridad", "一套专注于清晰阅读新闻的工具", "뉴스를 명확하게 읽기 위한 핵심 도구 모음"),
    ("Everything you need to judge an article—nothing you don't.", "Todo lo que necesitas para evaluar un artículo, y nada de más.", "判断一篇文章所需的一切功能，恰到好处。", "기사를 판단하는 데 필요한 기능만 담았습니다."),
    ("Bias classification with rationale", "Clasificación de sesgo con explicación", "带说明的倾向分类", "근거가 포함된 편향 분류"),
    ("Left / center / right paired with the specific cues that informed the call (framing, sources, wording).", "Izquierda / centro / derecha junto con las señales específicas que sustentan la evaluación (enfoque, fuentes, redacción).", "左 / 中 / 右结论会结合具体线索展示（框架、来源、措辞）。", "좌 / 중 / 우 결과와 함께 판단에 사용된 구체적 단서(프레이밍, 출처, 표현)를 보여줍니다."),
    ("Clear, skimmable summaries that preserve context and map claims to evidence.", "Resúmenes claros y fáciles de revisar que preservan el contexto y vinculan afirmaciones con evidencia.", "清晰易扫读的摘要，在保留语境的同时将观点对应到证据。", "맥락을 유지하면서 주장과 근거를 연결해 주는 명확하고 훑어보기 쉬운 요약을 제공합니다."),
    ("Private reading analytics", "Analítica privada de lectura", "私密阅读分析", "비공개 읽기 분석"),
    ("See trends in outlets and perspectives over time—stored locally by default.", "Observa tendencias en medios y perspectivas a lo largo del tiempo, almacenadas localmente por defecto.", "查看媒体来源和观点的长期趋势——默认本地存储。", "매체와 관점의 변화를 לאורך 시간에 따라 확인하세요. 기본적으로 로컬에 저장됩니다."),
    ("Flexible inputs", "Entradas flexibles", "灵活输入", "유연한 입력 방식"),
    ("Analyze URLs, pasted text, or PDFs. Robust parsing for long-form pieces.", "Analiza URL, texto pegado o PDF. Ofrece un procesamiento sólido para piezas extensas.", "支持分析 URL、粘贴文本或 PDF，并能稳健解析长篇内容。", "URL, 붙여넣은 텍스트, PDF를 분석할 수 있으며, 긴 글도 안정적으로 처리합니다."),
    ("Quality & controls", "Calidad y controles", "质量与控制", "품질 및 제어"),
    ("Deterministic modes for consistency and clear versioned outputs for sharing.", "Modos deterministas para mantener la consistencia y salidas versionadas claras para compartir.", "确定性模式保证结果一致，并提供清晰的版本化输出，便于分享。", "일관성을 위한 결정적 모드와 공유하기 쉬운 명확한 버전 출력이 제공됩니다."),
    ("Getting Started", "Primeros pasos", "快速开始", "시작하기"),
    ("How to Use FairRead", "Cómo usar FairRead", "如何使用 FairRead", "FairRead 사용 방법"),
    ("Follow three quick steps to analyze any news article with clarity and transparency.", "Sigue tres pasos rápidos para analizar cualquier artículo de noticias con claridad y transparencia.", "只需三个简单步骤，即可清晰透明地分析任何新闻文章。", "세 가지 간단한 단계로 어떤 뉴스 기사든 명확하고 투명하게 분석해 보세요."),
    ("1. Provide the article", "1. Proporciona el artículo", "1. 提供文章", "1. 기사 제공"),
    ("Enter a link, paste the text, or upload a PDF.", "Introduce un enlace, pega el texto o sube un PDF.", "输入链接、粘贴文本或上传 PDF。", "링크를 입력하거나 텍스트를 붙여넣거나 PDF를 업로드하세요."),
    ("2. Let AI analyze", "2. Deja que la IA analice", "2. 让 AI 分析", "2. AI 분석 시작"),
    ("FairRead detects political bias, highlights key signals, and summarizes the piece.", "FairRead detecta el sesgo político, resalta las señales clave y resume la pieza.", "FairRead 会识别政治倾向、突出关键信号，并总结文章内容。", "FairRead가 정치적 편향을 감지하고 핵심 신호를 강조하며 기사를 요약합니다."),
    ("3. Review insights", "3. Revisa los resultados", "3. 查看结果", "3. 결과 확인"),
    ("See the bias label, rationale, and a concise summary you can trust.", "Consulta la etiqueta de sesgo, la explicación y un resumen conciso en el que puedes confiar.", "查看倾向标签、分析理由以及值得信赖的简洁摘要。", "신뢰할 수 있는 편향 라벨, 근거, 간결한 요약을 확인하세요."),
    ("Community", "Comunidad", "社区", "커뮤니티"),
    ("Discuss, compare, and learn together", "Debatir, comparar y aprender juntos", "一起讨论、比较与学习", "함께 토론하고 비교하며 배워보세요"),
    ("Join focused debate rooms on live topics, compare evidence, and see how perspectives shift—without sacrificing civility or privacy.", "Únete a salas de debate enfocadas en temas actuales, compara evidencias y observa cómo cambian las perspectivas, sin sacrificar la cordialidad ni la privacidad.", "加入围绕热点话题的专题讨论室，比较证据，观察观点如何变化——同时不牺牲礼貌与隐私。", "현재 이슈에 대한 집중 토론방에 참여해 근거를 비교하고 관점의 변화를 살펴보세요. 예의와 개인정보 보호를 해치지 않습니다."),
    ("Explore Debate Rooms", "Explorar salas de debate", "探索辩论室", "토론방 살펴보기"),
    ("Topic-Focused Rooms", "Salas centradas en temas", "主题讨论室", "주제별 토론방"),
    ("Join curated rooms on specific policy issues. Keep discussions on track with structured prompts and timeboxed rounds.", "Únete a salas seleccionadas sobre cuestiones específicas de política pública. Mantén las conversaciones enfocadas con indicaciones estructuradas y rondas con tiempo definido.", "加入围绕特定政策议题精心策划的讨论室。通过结构化提示和限时轮次，让讨论保持聚焦。", "특정 정책 이슈에 맞춘 큐레이션 토론방에 참여하세요. 구조화된 프롬프트와 제한된 라운드로 논의를 주제에 맞게 유지합니다."),
    ("Weekly prompts and summaries", "Prompts y resúmenes semanales", "每周提示与摘要", "주간 프롬프트 및 요약"),
    ("Invite-only or public access", "Acceso por invitación o público", "仅限邀请或公开访问", "초대 전용 또는 공개 접근"),
    ("Evidence-Linked Posts", "Publicaciones vinculadas a evidencia", "证据关联帖子", "근거 연결 게시글"),
    ("Back claims with links or PDFs. FairRead highlights bias signals in cited content so participants can assess sources quickly.", "Respalda tus afirmaciones con enlaces o PDF. FairRead destaca señales de sesgo en el contenido citado para que las personas participantes evalúen las fuentes rápidamente.", "用链接或 PDF 支持您的观点。FairRead 会突出引用内容中的倾向信号，帮助参与者快速评估来源。", "링크나 PDF로 주장을 뒷받침하세요. FairRead가 인용된 콘텐츠의 편향 신호를 강조해 참가자들이 출처를 빠르게 평가할 수 있도록 돕습니다."),
    ("Inline article analysis", "Análisis de artículos en línea", "行内文章分析", "인라인 기사 분석"),
    ("Quote and counter-quote threads", "Hilos de cita y contracita", "引用与反驳线程", "인용 및 반박 스레드"),
    ("Civility & Privacy", "Civilidad y privacidad", "文明与隐私", "예의와 개인정보 보호"),
    ("Moderation tools and private rooms reduce noise. Participation history stays local by default; share only what you choose.", "Las herramientas de moderación y las salas privadas reducen el ruido. El historial de participación permanece local por defecto; comparte solo lo que elijas.", "审核工具和私密房间可减少噪音。参与历史默认保存在本地；只分享您愿意分享的内容。", "관리 도구와 비공개 방이 불필요한 잡음을 줄여 줍니다. 참여 기록은 기본적으로 로컬에 저장되며, 원하는 내용만 공유할 수 있습니다."),
    ("Report & mute controls", "Controles de denuncia y silencio", "举报与静音控制", "신고 및 음소거 기능"),
    ("Privacy-first analytics", "Analítica centrada en la privacidad", "隐私优先的分析", "개인정보 우선 분석"),
    ("Weekly Topic", "Tema semanal", "每周主题", "주간 주제"),
    ("Each week introduces a new debate prompt with a short neutral brief to frame the discussion.", "Cada semana se presenta una nueva propuesta de debate con un breve resumen neutral para enmarcar la discusión.", "每周都会推出新的辩题，并附上简短中立的导语来框定讨论。", "매주 새로운 토론 주제가 짧고 중립적인 안내문과 함께 제공되어 논의의 틀을 잡아 줍니다."),
    ("Structured Rounds", "Rondas estructuradas", "结构化轮次", "구조화된 라운드"),
    ("Opening statements, evidence posts, and closing remarks keep conversations concise and comparable.", "Las declaraciones iniciales, las publicaciones con evidencia y las conclusiones mantienen las conversaciones concisas y comparables.", "开场陈述、证据帖子和总结发言让讨论保持简洁且便于比较。", "모두발언, 근거 게시글, 마무리 발언으로 대화를 간결하고 비교 가능하게 유지합니다."),
    ("Outcome Snapshot", "Resumen del resultado", "结果概览", "결과 요약"),
    ("See a neutral wrap-up: main claims, strongest evidence cited, and perspective shift over the week.", "Consulta un cierre neutral: afirmaciones principales, evidencia más sólida citada y cambio de perspectiva a lo largo de la semana.", "查看中立总结：主要观点、最有力的引用证据，以及一周内观点的变化。", "한 주 동안의 주요 주장, 가장 강력한 근거, 관점의 변화를 중립적으로 정리해 보여줍니다."),
    ("© 2024~2026 FairRead. All Rights Reserved.", "© 2024~2026 FairRead. Todos los derechos reservados.", "© 2024~2026 FairRead. 版权所有。", "© 2024~2026 FairRead. 모든 권리 보유."),
]


def build_ui_labels():
    labels = {lang: OrderedDict() for lang in ("en", "es", "zh", "ko")}
    seen = set()
    for key, es, zh, ko in TRANSLATIONS:
        if key in seen:
            raise ValueError(f"Duplicate key detected: {key}")
        seen.add(key)
        labels["en"][key] = key
        labels["es"][key] = es
        labels["zh"][key] = zh
        labels["ko"][key] = ko
    if len(seen) * 4 < 280:
        raise ValueError("Expected at least 280 total translations.")
    return labels


def format_ui_labels(ui_labels):
    def q(value):
        return json.dumps(value, ensure_ascii=False)

    lines = ["UI_LABELS = {"]
    for lang in ("en", "es", "zh", "ko"):
        lines.append(f"    {q(lang)}: {{")
        for key, value in ui_labels[lang].items():
            lines.append(f"        {q(key)}: {q(value)},")
        lines.append("    },")
    lines.append("}")
    return "\n".join(lines)


def update_app(app_path):
    raw = app_path.read_bytes()
    newline = "\r\n" if b"\r\n" in raw else "\n"
    text = raw.decode("utf-8")
    start = text.index("UI_LABELS = {")
    end = text.index("\ndef translate_bias_label", start)
    block = format_ui_labels(build_ui_labels())
    updated = text[:start] + block + text[end:]
    with app_path.open("w", encoding="utf-8", newline=newline) as file:
        file.write(updated)


def main():
    parser = argparse.ArgumentParser(description="Generate localized UI_LABELS for FairRead.")
    parser.add_argument("--update-app", action="store_true", help="Replace UI_LABELS inside app.py.")
    args = parser.parse_args()

    ui_labels = build_ui_labels()
    if args.update_app:
        update_app(Path(__file__).with_name("app.py"))
        print(f"Updated app.py with {len(ui_labels['en'])} keys per language.")
    else:
        print(format_ui_labels(ui_labels))


if __name__ == "__main__":
    main()
