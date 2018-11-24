# from django.contrib.auth.models import User
# from django.shortcuts import render, redirect, get_object_or_404
# from .models import Board, Topic, Post
# from .forms import NewTopicForm
# #from django.http import Http404
# from django.contrib.auth.decorators import login_required

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from .forms import NewTopicForm, PostForm
from .models import Board, Post, Topic
from django.db.models import Count
from django.views.generic import View, CreateView, UpdateView
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import ListView


from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import get_object_or_404, render
from .models import Board




def home(request):
    boards = Board.objects.all()
    return render(request, 'home.html', {'boards': boards})

# def board_topics(request, pk):
#     board = get_object_or_404(Board, pk=pk)
#     topics = board.topics.order_by('-last_updated').annotate(replies=Count('posts') - 1)
#     return render(request, 'topics.html', {'board': board, 'topics': topics})


#FBV Pagination
def board_topics(request, pk):
    board = get_object_or_404(Board, pk=pk)
    queryset = board.topics.order_by('-last_updated').annotate(replies=Count('posts') - 1)
    page = request.GET.get('page', 1)

    paginator = Paginator(queryset, 10)

    try:
        topics = paginator.page(page)
    except PageNotAnInteger:
        # fallback to the first page
        topics = paginator.page(1)
    except EmptyPage:
        # probably the user tried to add a page number
        # in the url, so we fallback to the last page
        topics = paginator.page(paginator.num_pages)

    return render(request, 'topics.html', {'board': board, 'topics': topics})


@login_required
def new_topic(request, pk):
    board = get_object_or_404(Board, pk=pk)
    #user = User.objects.first()  # TODO: get the currently logged in user --- it was used to get the first user and simulate the login
    if request.method == 'POST':
        form = NewTopicForm(request.POST)
        if form.is_valid():
            topic = form.save(commit=False)
            topic.board = board
            topic.starter = request.user #user
            topic.save()
            post = Post.objects.create(
                message=form.cleaned_data.get('message'),
                topic=topic,
                created_by=request.user #user
            )
            return redirect('topic_posts', pk=pk, topic_pk=topic.pk)  # <- here
    else:
        form = NewTopicForm()
    return render(request, 'new_topic.html', {'board': board, 'form': form})

def topic_posts(request, pk, topic_pk):
    topic = get_object_or_404(Topic, board__pk=pk, pk=topic_pk)
    topic.views += 1
    topic.save()
    return render(request, 'topic_posts.html', {'topic': topic})

@login_required
def reply_topic(request, pk, topic_pk):
    topic = get_object_or_404(Topic, board__pk=pk, pk=topic_pk)
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.topic = topic
            post.created_by = request.user
            post.save()
            return redirect('topic_posts', pk=pk, topic_pk=topic_pk)
    else:
        form = PostForm()
    return render(request, 'reply_topic.html', {'topic': topic, 'form': form})

# # Function based View (FBV)
# def new_post(request):
#     if request.method == 'POST':
#         form = PostForm(request.POST)
#         if form.is_valid():
#             form.save()
#             return redirect('post_list')
#     else:
#         form = PostForm()
#     return render(request, 'new_post.html', {'form': form})
#
# # Class based View (CBV)
# class NewPostView(View):
#     def render(self, request):
#         return render(request, 'new_post.html', {'form': self.form})
#
#     def post(self, request):
#         self.form = PostForm(request.POST)
#         if self.form.is_valid():
#             self.form.save()
#             return redirect('post_list')
#         return self.render(request)
#
#     def get(self, request):
#         self.form = PostForm()
#         return self.render(request)

# # Generic Class based View (GCBV)
# class NewPostView(CreateView):
#     model = Post
#     form_class = PostForm
#     success_url = reverse_lazy('post_list')
#     template_name = 'new_post.html'


# We can’t decorate the class directly with the @login_required decorator.
# We have to use the utility @method_decorator, and pass a decorator (or a list of decorators) and tell which
# method should be decorated. In class-based views it’s common to decorate the dispatch method.
# It’s an internal method Django use (defined inside the View class). All requests pass through this method,
# so it’s safe to decorate it.

@method_decorator(login_required, name='dispatch')
class PostUpdateView(UpdateView):
    model = Post
    fields = ('message', )
    template_name = 'edit_post.html'
    pk_url_kwarg = 'post_pk'
    context_object_name = 'post'

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(created_by=self.request.user)

    def form_valid(self, form):
        post = form.save(commit=False)
        post.updated_by = self.request.user
        post.updated_at = timezone.now()
        post.save()
        return redirect('topic_posts', pk=post.topic.board.pk, topic_pk=post.topic.pk)

class BoardListView(ListView):
    model = Board
    context_object_name = 'boards'
    template_name = 'home.html'

#GCBV Pagination
class TopicListView(ListView):
    model = Topic
    context_object_name = 'topics'
    template_name = 'topics.html'
    paginate_by = 15

    def get_context_data(self, **kwargs):
        kwargs['board'] = self.board
        return super().get_context_data(**kwargs)

    def get_queryset(self):
        self.board = get_object_or_404(Board, pk=self.kwargs.get('pk'))
        queryset = self.board.topics.order_by('-last_updated').annotate(replies=Count('posts') - 1)
        return queryset

#Reusable Pagination Template
class PostListView(ListView):
    model = Post
    context_object_name = 'posts'
    template_name = 'topic_posts.html'
    paginate_by = 2

    def get_context_data(self, **kwargs):
        self.topic.views += 1
        self.topic.save()
        kwargs['topic'] = self.topic
        return super().get_context_data(**kwargs)

    def get_queryset(self):
        self.topic = get_object_or_404(Topic, board__pk=self.kwargs.get('pk'), pk=self.kwargs.get('topic_pk'))
        queryset = self.topic.posts.order_by('created_at')
        return queryset