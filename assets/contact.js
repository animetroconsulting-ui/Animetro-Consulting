(function () {
  var recipient = "mailto:consulting@animetro.ca";

  function field(form, name) {
    var element = form.elements[name];
    return element ? element.value.trim() : "";
  }

  function encodeMailtoComponent(value) {
    return encodeURIComponent(value).replace(/%0A/g, "%0D%0A");
  }

  function formatBody(form, language) {
    var name = field(form, "parent_name");
    var email = field(form, "email");
    var phoneWhatsapp = field(form, "phone_whatsapp");
    var wechat = field(form, "wechat");
    var gradeLevel = field(form, "grade_level");
    var currentSchool = field(form, "current_school");
    var serviceInterest = field(form, "service_interest");
    var targetSystem = field(form, "target_system");
    var mainQuestion = field(form, "main_question");
    var consultationLanguage = field(form, "consultation_language");
    var contactMethod = field(form, "contact_method");

    if (language === "zh") {
      return [
        "家长 / 监护人姓名：" + name,
        "電子郵件：" + email,
        "电话 / WhatsApp：" + phoneWhatsapp,
        "WeChat ID：" + wechat,
        "学生年级：" + gradeLevel,
        "当前学校 / 学校体系：" + currentSchool,
        "感兴趣的服务：" + serviceInterest,
        "目标国家或教育体系：" + targetSystem,
        "偏好的咨询语言：" + consultationLanguage,
        "偏好的联系方式：" + contactMethod,
        "",
        "主要问题或关注点：",
        mainQuestion
      ].join("\n");
    }

    return [
      "Parent / Guardian Name: " + name,
      "Email: " + email,
      "Phone / WhatsApp: " + phoneWhatsapp,
      "WeChat ID: " + wechat,
      "Student's Grade Level: " + gradeLevel,
      "Current School / School System: " + currentSchool,
      "Service of Interest: " + serviceInterest,
      "Target Country or Education System: " + targetSystem,
      "Preferred Consultation Language: " + consultationLanguage,
      "Preferred Contact Method: " + contactMethod,
      "",
      "Main Question or Concern:",
      mainQuestion
    ].join("\n");
  }

  function subjectFor(language) {
    return language === "zh"
      ? "艾美加教育顾问免费私人咨询"
      : "Book a Free Private Consultation";
  }

  document.querySelectorAll("[data-contact-form]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();

      var language = form.getAttribute("data-language") || "en";
      var subject = encodeMailtoComponent(subjectFor(language));
      var body = encodeMailtoComponent(formatBody(form, language));

      window.location.href = recipient + "?subject=" + subject + "&body=" + body;
    });
  });
})();
