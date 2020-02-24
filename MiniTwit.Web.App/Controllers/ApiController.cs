using System;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;
using MiniTwit.Entities;
using MiniTwit.Models;
using Newtonsoft.Json;

namespace MiniTwit.Web.App.Controllers
{
    public class ApiController : Controller
    {
        
        private readonly ILogger<ApiController> _logger;
        private readonly IMessageRepository _messageRepository;
        private readonly IUserRepository _userRepository;
        private readonly UserManager<User> _userManager;

        public ApiController(UserManager<User> userManager, ILogger<ApiController> logger, IMessageRepository messageRepository,
            IUserRepository userRepository)
        {
            _userManager = userManager;
            _logger = logger;
            _messageRepository = messageRepository;
            _userRepository = userRepository;
        }

        //This function is defined, dont know if we need to use it.
        private (bool, IActionResult) NotRequestFromSimulator()
        {
            if (HttpContext.Request.Headers["Authorization"].Equals("Basic c2ltdWxhdG9yOnN1cGVyX3NhZmUh"))
            {
                return (false, null);
            }

            return (true, StatusCode(403, Json(new {status = 403, error_msg = "You are not authorized to use this resource!"})));
        }
        
        [Route("[controller]/msgs/")]
        [HttpGet]
        [AllowAnonymous]
        public async Task<IActionResult> GetMessages([FromQuery(Name = "no")] int number = 100)
        {
            var messages= (await _messageRepository.ReadAsync())
                            .Take(number)
                            .Select(m => new {content=m.Text, pub_date=m.PubDate, user=m.Author.UserName});
            if (messages.Any())
                return Json(messages);
            else
                return StatusCode(204, Json(""));
        }
        
        [Route("[controller]/msgs/{id}")]
        [HttpGet]
        [AllowAnonymous]
        public async Task<IActionResult> UserGetMessages(int id, [FromQuery(Name = "no")] int number = 100)
        {
            var messages = (await _messageRepository.ReadAllMessagesFromUserAsync(id))
                .Take(number)
                .Select(m => new {content=m.Text, pub_date=m.PubDate, user=m.Author.UserName});
            return Json(messages.Take(number));
        }


        public class MessagePost
        {
            public string Content { get; set; }
        }
        
        [Route("[controller]/msgs/{id}")]
        [HttpPost]
        [AllowAnonymous]
        public async Task<IActionResult> UserPostMessages(int id, [FromBody] MessagePost messagePost)
        {
            var user = await _userRepository.ReadAsync(id);
            if (user == null || messagePost?.Content == null)
            {
                return NotFound();
            }
            var message = new Message
            {
                Author =  user,
                AuthorId = user.Id,
                Flagged = 0,
                PubDate = DateTime.Now,
                Text = messagePost.Content
            };
            await _messageRepository.CreateAsync(message);
            return StatusCode(204, "");
        }

        public class RegisterPost
        {
            public string Username { get; set; }
            public string Email { get; set; }
            public string Pwd { get; set; }
            
        }
        [Route("[controller]/register")]
        [HttpPost]
        [AllowAnonymous]
        public async Task<IActionResult> RegisterUser([FromBody] RegisterPost registerPost)
        {
            if (registerPost?.Username == null)
            {
                return StatusCode(403,
                    Json(new {status = 400, error_msg = "You have to enter a username"}));
            }
            if (registerPost.Email == null || !registerPost.Email.Contains("@"))
            {
                return StatusCode(403,
                    Json(new {status = 400, error_msg = "You have to enter a valid email address"}));
            }
            if (registerPost.Pwd == null)
            {
                return StatusCode(403,
                    Json(new {status = 400, error_msg = "You have to enter a password"}));
            }
            if ((await _userRepository.ReadAsyncByUsername(registerPost.Username)) != null)
            {
                return StatusCode(403,
                    Json(new {status = 400, error_msg = "The username is already taken"}));
            }
            var user = new User
            {
                UserName = registerPost.Username,
                Email = registerPost.Email
            };
            var result = await _userManager.CreateAsync(user, registerPost.Pwd);
            _logger.LogInformation(registerPost.Username + " created a new account with password.");
            return StatusCode(204, "");
        }
        
        
    }
}